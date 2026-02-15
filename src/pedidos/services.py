from django.db import transaction

from .models import StatusPedido
from .state_machine import PedidoStateMachine
from .repositories import (
    PedidoRepository, ItemPedidoRepository, HistoricoStatusPedidoRepository, ClienteRepository,
    ProdutoRepository,
)


class PedidoNaoEncontradoError(Exception):
    pass


class AlterarStatusPedidoService:
    def __init__(self):
        self.pedido_repository = PedidoRepository()
        self.historico_repository = HistoricoStatusPedidoRepository()
    
    @transaction.atomic
    def executar(self, pedido_id, novo_status, alterado_por=None):
        
        pedido = self._obter_pedido_com_lock(pedido_id)
        
        status_anterior = pedido.status
        
        state_machine = PedidoStateMachine(status_anterior)
        state_machine.validar(novo_status)
        
        self.pedido_repository.atualizar_status(pedido, novo_status)
        
        self._registrar_historico(
            pedido=pedido,
            status_anterior=status_anterior,
            status_novo=novo_status,
            alterado_por=alterado_por
        )
        
        return pedido
    
    def _obter_pedido_com_lock(self, pedido_id):
        pedido = self.pedido_repository.obter_com_lock(pedido_id)
        if pedido is None:
            raise PedidoNaoEncontradoError(
                f"Pedido com ID {pedido_id} não encontrado"
            )
        return pedido
    
    def _registrar_historico(self, pedido, status_anterior, status_novo, alterado_por):
        return self.historico_repository.criar(
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
    def __init__(self):
        self.pedido_repository = PedidoRepository()
        self.item_pedido_repository = ItemPedidoRepository()
        self.cliente_repository = ClienteRepository()
        self.produto_repository = ProdutoRepository()
    
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
        return self.pedido_repository.obter_por_chave_idempotencia(chave)
    
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
        from decimal import Decimal
        
        cliente = self._obter_cliente_ativo(cliente_id)
        
        produtos_ids = [item['produto_id'] for item in itens]
        produtos = self.produto_repository.obter_por_ids_com_lock(produtos_ids)
        
        produtos_map = {p.id: p for p in produtos}
        self._validar_produtos_e_estoque(itens, produtos_map, produtos_ids)
        
        pedido = self.pedido_repository.criar(
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
            
            self.item_pedido_repository.criar(
                pedido=pedido,
                produto=produto,
                quantidade=quantidade,
                preco_unitario=preco_unitario,
                subtotal=subtotal
            )
            
            self.produto_repository.decrementar_estoque(produto, quantidade)
            
            valor_total += subtotal
        
        self.pedido_repository.atualizar_valor_total(pedido, valor_total)
        
        return pedido
    
    def _obter_cliente_ativo(self, cliente_id):
        cliente = self.cliente_repository.obter_por_id(cliente_id)
        
        if cliente is None:
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
    def __init__(self):
        self.pedido_repository = PedidoRepository()
        self.produto_repository = ProdutoRepository()
        self.historico_repository = HistoricoStatusPedidoRepository()
    
    @transaction.atomic
    def executar(self, pedido_id, cancelado_por=None, motivo=None):
        from .events import EventoPedido, emitir_evento
        
        pedido = self._obter_pedido_com_lock(pedido_id)
        
        if pedido.status == StatusPedido.CANCELADO:
            return pedido
        
        status_anterior = pedido.status
        self._validar_pode_cancelar(pedido)
        
        itens = self.pedido_repository.obter_itens(pedido)
        
        if itens:
            produto_ids = [item.produto_id for item in itens]
            produtos = self.produto_repository.obter_por_ids_com_lock(produto_ids)
            produtos_map = {p.id: p for p in produtos}
            
            self._devolver_estoque(itens, produtos_map)
        
        observacoes = pedido.observacoes
        if motivo:
            observacoes = f"{observacoes or ''}\n[CANCELAMENTO] {motivo}".strip()
        
        self.pedido_repository.atualizar_status_e_observacoes(
            pedido, StatusPedido.CANCELADO, observacoes
        )
        
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
        pedido = self.pedido_repository.obter_com_lock(pedido_id)
        if pedido is None:
            raise PedidoNaoEncontradoError(
                f"Pedido com ID {pedido_id} não encontrado"
            )
        return pedido
    
    def _validar_pode_cancelar(self, pedido):
        state_machine = PedidoStateMachine(pedido.status)
        
        if not state_machine.pode_cancelar():
            raise PedidoNaoPodeCancelarError(
                f"Pedido '{pedido.numero}' não pode ser cancelado. "
                f"Status atual: {pedido.status}. "
                f"Transições permitidas: {state_machine.obter_transicoes_permitidas()}"
            )
    
    def _devolver_estoque(self, itens, produtos_map):
        for item in itens:
            produto = produtos_map.get(item.produto_id)
            if produto:
                self.produto_repository.incrementar_estoque(produto, item.quantidade)
    
    def _registrar_historico(self, pedido, status_anterior, cancelado_por):
        return self.historico_repository.criar(
            pedido=pedido,
            status_anterior=status_anterior,
            status_novo=StatusPedido.CANCELADO,
            alterado_por=cancelado_por
        )
