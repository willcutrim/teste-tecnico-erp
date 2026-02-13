from django.db import transaction

from .models import Pedido, HistoricoStatusPedido
from .state_machine import PedidoStateMachine, TransicaoInvalidaError


class PedidoNaoEncontradoError(Exception):
    pass


class AlterarStatusPedidoService:
    @transaction.atomic
    def executar(self, pedido_id, novo_status, alterado_por=None):
        
        pedido = self._obter_pedido_com_lock(pedido_id)
        
        status_anterior = pedido.status
        
        state_machine = PedidoStateMachine(status_anterior)
        state_machine.validar(novo_status)
        
        pedido.status = novo_status
        pedido.save(update_fields=['status', 'updated_at'])
        
        self._registrar_historico(
            pedido=pedido,
            status_anterior=status_anterior,
            status_novo=novo_status,
            alterado_por=alterado_por
        )
        
        return pedido
    
    def _obter_pedido_com_lock(self, pedido_id):
        try:
            return Pedido.objects.select_for_update().get(id=pedido_id)
        except Pedido.DoesNotExist:
            raise PedidoNaoEncontradoError(
                f"Pedido com ID {pedido_id} não encontrado"
            )
    
    def _registrar_historico(self, pedido, status_anterior, status_novo, alterado_por):
        return HistoricoStatusPedido.objects.create(
            pedido=pedido,
            status_anterior=status_anterior,
            status_novo=status_novo,
            alterado_por=alterado_por
        )


class ClienteNaoEncontradoError(Exception):
    pass


class ClienteInativoError(Exception):
    pass


class ProdutoNaoEncontradoError(Exception):
    pass


class ProdutoInativoError(Exception):
    pass


class EstoqueInsuficienteError(Exception):
    def __init__(self, produto_id, produto_nome, disponivel, solicitado):
        self.produto_id = produto_id
        self.produto_nome = produto_nome
        self.disponivel = disponivel
        self.solicitado = solicitado
        super().__init__(
            f"Estoque insuficiente para '{produto_nome}': "
            f"disponível={disponivel}, solicitado={solicitado}"
        )


class QuantidadeInvalidaError(Exception):
    pass


class ItensVaziosError(Exception):
    pass


class CriarPedidoService:
    def executar(self, cliente_id, itens, chave_idempotencia, observacoes=None):
        pedido_existente = self._buscar_pedido_por_idempotencia(chave_idempotencia)
        if pedido_existente:
            return pedido_existente, False
        
        if not itens:
            raise ItensVaziosError("O pedido deve conter pelo menos um item")
        
        self._validar_quantidades(itens)
        
        pedido = self._criar_pedido_atomico(
            cliente_id=cliente_id,
            itens=itens,
            chave_idempotencia=chave_idempotencia,
            observacoes=observacoes
        )
        
        return pedido, True
    
    def _buscar_pedido_por_idempotencia(self, chave):
        try:
            return Pedido.objects.get(chave_idempotencia=chave)
        except Pedido.DoesNotExist:
            return None
    
    def _validar_quantidades(self, itens):
        for item in itens:
            qtd = item.get('quantidade', 0)
            if qtd <= 0:
                raise QuantidadeInvalidaError(
                    f"Quantidade deve ser maior que zero. "
                    f"Produto ID {item.get('produto_id')} com quantidade {qtd}"
                )
    
    @transaction.atomic
    def _criar_pedido_atomico(self, cliente_id, itens, chave_idempotencia, observacoes):
        from clientes.models import Cliente
        from produtos.models import Produto
        from .models import ItemPedido, StatusPedido
        from decimal import Decimal
        
        cliente = self._obter_cliente_ativo(cliente_id, Cliente)
        
        produtos_ids = [item['produto_id'] for item in itens]
        produtos = self._obter_produtos_com_lock(produtos_ids, Produto)
        
        produtos_map = {p.id: p for p in produtos}
        self._validar_produtos_e_estoque(itens, produtos_map, produtos_ids)
        
        pedido = Pedido.objects.create(
            cliente=cliente,
            status=StatusPedido.PENDENTE,
            chave_idempotencia=chave_idempotencia,
            observacoes=observacoes,
            valor_total=Decimal('0.00')
        )
        
        valor_total = Decimal('0.00')
        
        for item_data in itens:
            produto = produtos_map[item_data['produto_id']]
            quantidade = item_data['quantidade']
            preco_unitario = produto.preco
            subtotal = preco_unitario * quantidade
            
            ItemPedido.objects.create(
                pedido=pedido,
                produto=produto,
                quantidade=quantidade,
                preco_unitario=preco_unitario,
                subtotal=subtotal
            )
            
            produto.quantidade_estoque -= quantidade
            produto.save(update_fields=['quantidade_estoque', 'updated_at'])
            
            valor_total += subtotal
        
        pedido.valor_total = valor_total
        pedido.save(update_fields=['valor_total'])
        
        return pedido
    
    def _obter_cliente_ativo(self, cliente_id, Cliente):
        try:
            cliente = Cliente.all_objects.get(id=cliente_id)
        except Cliente.DoesNotExist:
            raise ClienteNaoEncontradoError(
                f"Cliente com ID {cliente_id} não encontrado"
            )
        
        if cliente.deleted_at is not None:
            raise ClienteNaoEncontradoError(
                f"Cliente com ID {cliente_id} não encontrado"
            )
        
        if not cliente.ativo:
            raise ClienteInativoError(
                f"Cliente '{cliente.nome}' está inativo"
            )
        
        return cliente
    
    def _obter_produtos_com_lock(self, produtos_ids, Produto):
        return list(
            Produto.all_objects
            .select_for_update()
            .filter(id__in=produtos_ids)
            .order_by('id')
        )
    
    def _validar_produtos_e_estoque(self, itens, produtos_map, produtos_ids):
        for item_data in itens:
            produto_id = item_data['produto_id']
            quantidade = item_data['quantidade']
            
            if produto_id not in produtos_map:
                raise ProdutoNaoEncontradoError(
                    f"Produto com ID {produto_id} não encontrado"
                )
            
            produto = produtos_map[produto_id]
            
            if produto.deleted_at is not None:
                raise ProdutoNaoEncontradoError(
                    f"Produto com ID {produto_id} não encontrado"
                )
            
            if not produto.ativo:
                raise ProdutoInativoError(
                    f"Produto '{produto.nome}' está inativo"
                )
            
            if produto.quantidade_estoque < quantidade:
                raise EstoqueInsuficienteError(
                    produto_id=produto.id,
                    produto_nome=produto.nome,
                    disponivel=produto.quantidade_estoque,
                    solicitado=quantidade
                )


class PedidoNaoPodeCancelarError(Exception):
    pass


class CancelarPedidoService:
    @transaction.atomic
    def executar(self, pedido_id, cancelado_por=None, motivo=None):
        from produtos.models import Produto
        from .models import StatusPedido
        from .events import EventoPedido, emitir_evento
        
        pedido = self._obter_pedido_com_lock(pedido_id)
        
        if pedido.status == StatusPedido.CANCELADO:
            return pedido
        
        status_anterior = pedido.status
        self._validar_pode_cancelar(pedido)
        
        itens = list(pedido.itens.all())
        
        if itens:
            produtos = self._obter_produtos_com_lock(itens, Produto)
            produtos_map = {p.id: p for p in produtos}
            
            self._devolver_estoque(itens, produtos_map)
        
        pedido.status = StatusPedido.CANCELADO
        if motivo:
            pedido.observacoes = f"{pedido.observacoes or ''}\n[CANCELAMENTO] {motivo}".strip()
        pedido.save(update_fields=['status', 'observacoes', 'updated_at'])
        
        self._registrar_historico(
            pedido=pedido,
            status_anterior=status_anterior,
            cancelado_por=cancelado_por
        )
        
        emitir_evento(
            EventoPedido.PEDIDO_CANCELADO,
            {
                'pedido_id': pedido.id,
                'numero': pedido.numero,
                'cliente_id': pedido.cliente_id,
                'status_anterior': status_anterior,
                'cancelado_por': cancelado_por,
                'motivo': motivo,
            }
        )
        
        return pedido
    
    def _obter_pedido_com_lock(self, pedido_id):
        try:
            return Pedido.objects.select_for_update().get(id=pedido_id)
        except Pedido.DoesNotExist:
            raise PedidoNaoEncontradoError(
                f"Pedido com ID {pedido_id} não encontrado"
            )
    
    def _validar_pode_cancelar(self, pedido):
        from .models import StatusPedido
        
        state_machine = PedidoStateMachine(pedido.status)
        
        if not state_machine.pode_cancelar():
            raise PedidoNaoPodeCancelarError(
                f"Pedido '{pedido.numero}' não pode ser cancelado. "
                f"Status atual: {pedido.status}. "
                f"Transições permitidas: {state_machine.obter_transicoes_permitidas()}"
            )
    
    def _obter_produtos_com_lock(self, itens, Produto):
        produto_ids = [item.produto_id for item in itens]
        return list(
            Produto.all_objects
            .select_for_update()
            .filter(id__in=produto_ids)
            .order_by('id')
        )
    
    def _devolver_estoque(self, itens, produtos_map):
        for item in itens:
            produto = produtos_map.get(item.produto_id)
            if produto:
                produto.quantidade_estoque += item.quantidade
                produto.save(update_fields=['quantidade_estoque', 'updated_at'])
    
    def _registrar_historico(self, pedido, status_anterior, cancelado_por):
        from .models import StatusPedido
        
        return HistoricoStatusPedido.objects.create(
            pedido=pedido,
            status_anterior=status_anterior,
            status_novo=StatusPedido.CANCELADO,
            alterado_por=cancelado_por
        )
