from decimal import Decimal
from django.db import transaction

from .models import Pedido, ItemPedido, HistoricoStatusPedido, StatusPedido


class PedidoRepository:
    
    def obter_por_id(self, pedido_id):
        try:
            return Pedido.objects.get(id=pedido_id)
        except Pedido.DoesNotExist:
            return None
    
    def obter_com_lock(self, pedido_id):
        try:
            return Pedido.objects.select_for_update().get(id=pedido_id)
        except Pedido.DoesNotExist:
            return None
    
    def obter_por_chave_idempotencia(self, chave):
        try:
            return Pedido.objects.get(chave_idempotencia=chave)
        except Pedido.DoesNotExist:
            return None
    
    def criar(self, cliente, status, chave_idempotencia, observacoes=None, valor_total=None):
        return Pedido.objects.create(
            cliente=cliente,
            status=status,
            chave_idempotencia=chave_idempotencia,
            observacoes=observacoes,
            valor_total=valor_total or Decimal('0.00')
        )
    
    def atualizar_status(self, pedido, novo_status):
        pedido.status = novo_status
        pedido.save(update_fields=['status', 'updated_at'])
        return pedido
    
    def atualizar_valor_total(self, pedido, valor_total):
        pedido.valor_total = valor_total
        pedido.save(update_fields=['valor_total'])
        return pedido
    
    def atualizar_observacoes(self, pedido, observacoes):
        pedido.observacoes = observacoes
        pedido.save(update_fields=['observacoes', 'updated_at'])
        return pedido
    
    def atualizar_status_e_observacoes(self, pedido, status, observacoes):
        pedido.status = status
        pedido.observacoes = observacoes
        pedido.save(update_fields=['status', 'observacoes', 'updated_at'])
        return pedido
    
    def obter_itens(self, pedido):
        return list(pedido.itens.all())


class ItemPedidoRepository:
    def criar(self, pedido, produto, quantidade, preco_unitario, subtotal):
        return ItemPedido.objects.create(
            pedido=pedido,
            produto=produto,
            quantidade=quantidade,
            preco_unitario=preco_unitario,
            subtotal=subtotal
        )


class HistoricoStatusPedidoRepository:
    def criar(self, pedido, status_anterior, status_novo, alterado_por=None):
        return HistoricoStatusPedido.objects.create(
            pedido=pedido,
            status_anterior=status_anterior,
            status_novo=status_novo,
            alterado_por=alterado_por
        )


class ClienteRepository:
    def obter_por_id(self, cliente_id):
        from clientes.models import Cliente
        try:
            return Cliente.all_objects.get(id=cliente_id)
        except Cliente.DoesNotExist:
            return None


class ProdutoRepository:
    def obter_por_ids_com_lock(self, produto_ids):
        from produtos.models import Produto
        return list(
            Produto.all_objects
            .select_for_update()
            .filter(id__in=produto_ids)
            .order_by('id')
        )
    
    def atualizar_estoque(self, produto, nova_quantidade):
        produto.quantidade_estoque = nova_quantidade
        produto.save(update_fields=['quantidade_estoque', 'updated_at'])
        return produto
    
    def decrementar_estoque(self, produto, quantidade):
        produto.quantidade_estoque -= quantidade
        produto.save(update_fields=['quantidade_estoque', 'updated_at'])
        return produto
    
    def incrementar_estoque(self, produto, quantidade):
        produto.quantidade_estoque += quantidade
        produto.save(update_fields=['quantidade_estoque', 'updated_at'])
        return produto
