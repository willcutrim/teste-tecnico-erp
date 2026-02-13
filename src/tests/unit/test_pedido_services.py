import pytest
from decimal import Decimal

from pedidos.services import (
    CriarPedidoService, CancelarPedidoService, AlterarStatusPedidoService, ClienteNaoEncontradoError,
    ClienteInativoError, ProdutoNaoEncontradoError, ProdutoInativoError, EstoqueInsuficienteError,
    ItensVaziosError, QuantidadeInvalidaError, PedidoNaoEncontradoError, PedidoNaoPodeCancelarError,
)
from pedidos.state_machine import TransicaoInvalidaError, StatusPedido


class TestCriarPedidoService:
    
    def test_criar_pedido_com_sucesso(self, cliente_ativo, produto_com_estoque):
        service = CriarPedidoService()
        
        pedido, criado = service.executar(
            cliente_id=cliente_ativo.id,
            itens=[{'produto_id': produto_com_estoque.id, 'quantidade': 2}],
            chave_idempotencia='teste-criar-001'
        )
        
        assert criado is True
        assert pedido.cliente == cliente_ativo
        assert pedido.status == StatusPedido.PENDENTE
        assert pedido.valor_total == Decimal('200.00')
        assert pedido.itens.count() == 1
    
    def test_criar_pedido_decrementa_estoque(self, cliente_ativo, produto_com_estoque):
        estoque_inicial = produto_com_estoque.quantidade_estoque
        service = CriarPedidoService()
        
        service.executar(
            cliente_id=cliente_ativo.id,
            itens=[{'produto_id': produto_com_estoque.id, 'quantidade': 3}],
            chave_idempotencia='teste-estoque-001'
        )
        
        produto_com_estoque.refresh_from_db()
        assert produto_com_estoque.quantidade_estoque == estoque_inicial - 3
    
    def test_criar_pedido_cliente_inexistente(self, produto_com_estoque):
        service = CriarPedidoService()
        
        with pytest.raises(ClienteNaoEncontradoError):
            service.executar(
                cliente_id=99999,
                itens=[{'produto_id': produto_com_estoque.id, 'quantidade': 1}],
                chave_idempotencia='teste-cliente-inexistente'
            )
    
    def test_criar_pedido_cliente_inativo(self, cliente_inativo, produto_com_estoque):
        service = CriarPedidoService()
        
        with pytest.raises(ClienteInativoError):
            service.executar(
                cliente_id=cliente_inativo.id,
                itens=[{'produto_id': produto_com_estoque.id, 'quantidade': 1}],
                chave_idempotencia='teste-cliente-inativo'
            )
    
    def test_criar_pedido_produto_inexistente(self, cliente_ativo):
        service = CriarPedidoService()
        
        with pytest.raises(ProdutoNaoEncontradoError):
            service.executar(
                cliente_id=cliente_ativo.id,
                itens=[{'produto_id': 99999, 'quantidade': 1}],
                chave_idempotencia='teste-produto-inexistente'
            )
    
    def test_criar_pedido_produto_inativo(self, cliente_ativo, produto_inativo):
        service = CriarPedidoService()
        
        with pytest.raises(ProdutoInativoError):
            service.executar(
                cliente_id=cliente_ativo.id,
                itens=[{'produto_id': produto_inativo.id, 'quantidade': 1}],
                chave_idempotencia='teste-produto-inativo'
            )
    
    def test_criar_pedido_estoque_insuficiente(self, cliente_ativo, produto_com_estoque):
        service = CriarPedidoService()
        
        with pytest.raises(EstoqueInsuficienteError) as exc_info:
            service.executar(
                cliente_id=cliente_ativo.id,
                itens=[{'produto_id': produto_com_estoque.id, 'quantidade': 100}],
                chave_idempotencia='teste-estoque-insuficiente'
            )
        
        assert exc_info.value.disponivel == 10
        assert exc_info.value.solicitado == 100
    
    def test_criar_pedido_itens_vazios(self, cliente_ativo):
        service = CriarPedidoService()
        
        with pytest.raises(ItensVaziosError):
            service.executar(
                cliente_id=cliente_ativo.id,
                itens=[],
                chave_idempotencia='teste-itens-vazios'
            )
    
    def test_criar_pedido_quantidade_invalida(self, cliente_ativo, produto_com_estoque):
        service = CriarPedidoService()
        
        with pytest.raises(QuantidadeInvalidaError):
            service.executar(
                cliente_id=cliente_ativo.id,
                itens=[{'produto_id': produto_com_estoque.id, 'quantidade': 0}],
                chave_idempotencia='teste-quantidade-invalida'
            )


class TestCancelarPedidoService:
    def test_cancelar_pedido_com_sucesso(self, pedido_pendente):
        service = CancelarPedidoService()
        
        pedido = service.executar(
            pedido_id=pedido_pendente.id,
            cancelado_por='teste@sistema.com',
            motivo='Teste de cancelamento'
        )
        
        assert pedido.status == StatusPedido.CANCELADO
    
    def test_cancelar_pedido_devolve_estoque(self, db, cliente_ativo, produto_com_estoque):
        from pedidos.services import CriarPedidoService
        
        estoque_inicial = produto_com_estoque.quantidade_estoque
        
        criar_service = CriarPedidoService()
        pedido, _ = criar_service.executar(
            cliente_id=cliente_ativo.id,
            itens=[{'produto_id': produto_com_estoque.id, 'quantidade': 3}],
            chave_idempotencia='teste-devolucao-estoque'
        )
        
        produto_com_estoque.refresh_from_db()
        assert produto_com_estoque.quantidade_estoque == estoque_inicial - 3
        
        cancelar_service = CancelarPedidoService()
        cancelar_service.executar(pedido_id=pedido.id)
        
        produto_com_estoque.refresh_from_db()
        assert produto_com_estoque.quantidade_estoque == estoque_inicial
    
    def test_cancelar_pedido_inexistente(self, db):
        service = CancelarPedidoService()
        
        with pytest.raises(PedidoNaoEncontradoError):
            service.executar(pedido_id=99999)
    
    def test_cancelar_pedido_ja_cancelado_idempotente(self, pedido_pendente):
        service = CancelarPedidoService()
        
        service.executar(pedido_id=pedido_pendente.id)
        
        pedido = service.executar(pedido_id=pedido_pendente.id)
        
        assert pedido.status == StatusPedido.CANCELADO
    
    def test_cancelar_pedido_entregue_falha(self, db, cliente_ativo):
        from pedidos.models import Pedido
        
        pedido = Pedido.objects.create(
            cliente=cliente_ativo,
            status=StatusPedido.ENTREGUE,
            valor_total=Decimal('100.00'),
            chave_idempotencia='pedido-entregue-001'
        )
        
        service = CancelarPedidoService()
        
        with pytest.raises(PedidoNaoPodeCancelarError):
            service.executar(pedido_id=pedido.id)


class TestAlterarStatusPedidoService:
    def test_alterar_status_pendente_para_confirmado(self, pedido_pendente):
        service = AlterarStatusPedidoService()
        
        pedido = service.executar(
            pedido_id=pedido_pendente.id,
            novo_status=StatusPedido.CONFIRMADO,
            alterado_por='teste@sistema.com'
        )
        
        assert pedido.status == StatusPedido.CONFIRMADO
    
    def test_alterar_status_registra_historico(self, pedido_pendente):
        service = AlterarStatusPedidoService()
        
        service.executar(
            pedido_id=pedido_pendente.id,
            novo_status=StatusPedido.CONFIRMADO,
            alterado_por='usuario@teste.com'
        )
        
        historico = pedido_pendente.historico_status.first()
        assert historico is not None
        assert historico.status_anterior == StatusPedido.PENDENTE
        assert historico.status_novo == StatusPedido.CONFIRMADO
        assert historico.alterado_por == 'usuario@teste.com'
    
    def test_alterar_status_transicao_invalida(self, pedido_pendente):
        service = AlterarStatusPedidoService()
        
        with pytest.raises(TransicaoInvalidaError):
            service.executar(
                pedido_id=pedido_pendente.id,
                novo_status=StatusPedido.ENVIADO
            )
    
    def test_alterar_status_pedido_inexistente(self, db):
        service = AlterarStatusPedidoService()
        
        with pytest.raises(PedidoNaoEncontradoError):
            service.executar(
                pedido_id=99999,
                novo_status=StatusPedido.CONFIRMADO
            )
