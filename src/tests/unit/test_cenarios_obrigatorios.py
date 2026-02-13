import pytest
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor, as_completed
from django.db import connection
from django.conf import settings

from pedidos.services import (
    CriarPedidoService,
    EstoqueInsuficienteError,
)
from pedidos.state_machine import StatusPedido


# Helper para verificar se está usando SQLite
def usando_sqlite():
    return 'sqlite' in settings.DATABASES['default']['ENGINE']


@pytest.mark.django_db(transaction=True)
@pytest.mark.skipif(usando_sqlite(), reason="SQLite não suporta concorrência adequada")
class TestConcorrenciaEstoque:
    def test_dois_pedidos_simultaneos_mesmo_produto(self):
       
        from clientes.models import Cliente
        from produtos.models import Produto
        
        cliente = Cliente.objects.create(
            nome='Cliente Concorrência',
            cpf_cnpj='11111111111',
            email='concorrencia@teste.com',
            ativo=True
        )
        
        produto = Produto.objects.create(
            sku='CONC-001',
            nome='Produto Concorrência',
            preco=Decimal('100.00'),
            quantidade_estoque=10,
            ativo=True
        )
        
        resultados = {'sucesso': 0, 'falha': 0}
        erros = []
        
        def criar_pedido(chave):
            """Função para criar pedido em thread separada."""
            # Cada thread precisa de sua própria conexão
            connection.close()
            
            try:
                service = CriarPedidoService()
                service.executar(
                    cliente_id=cliente.id,
                    itens=[{'produto_id': produto.id, 'quantidade': 8}],
                    chave_idempotencia=chave
                )
                return 'sucesso'
            except EstoqueInsuficienteError as e:
                erros.append(str(e))
                return 'falha'
        
        # Executa dois pedidos em paralelo
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(criar_pedido, 'conc-pedido-1'),
                executor.submit(criar_pedido, 'conc-pedido-2'),
            ]
            
            for future in as_completed(futures):
                resultado = future.result()
                resultados[resultado] += 1
        
        assert resultados['sucesso'] == 1, f"Esperado 1 sucesso, obtido {resultados['sucesso']}"
        assert resultados['falha'] == 1, f"Esperado 1 falha, obtido {resultados['falha']}"
        
        produto.refresh_from_db()
        assert produto.quantidade_estoque == 2, f"Estoque deveria ser 2, mas é {produto.quantidade_estoque}"


@pytest.mark.django_db
class TestIdempotencia:
    def test_tres_pedidos_mesma_chave_idempotencia(self, cliente_ativo, produto_com_estoque):
        from pedidos.models import Pedido
        
        service = CriarPedidoService()
        chave = 'idempotencia-teste-001'
        estoque_inicial = produto_com_estoque.quantidade_estoque
        
        pedido1, criado1 = service.executar(
            cliente_id=cliente_ativo.id,
            itens=[{'produto_id': produto_com_estoque.id, 'quantidade': 2}],
            chave_idempotencia=chave
        )
        
        pedido2, criado2 = service.executar(
            cliente_id=cliente_ativo.id,
            itens=[{'produto_id': produto_com_estoque.id, 'quantidade': 2}],
            chave_idempotencia=chave
        )
        
        pedido3, criado3 = service.executar(
            cliente_id=cliente_ativo.id,
            itens=[{'produto_id': produto_com_estoque.id, 'quantidade': 2}],
            chave_idempotencia=chave
        )
        
        # Validações
        assert criado1 is True, "Primeiro pedido deveria ser criado"
        assert criado2 is False, "Segundo pedido não deveria ser criado (idempotente)"
        assert criado3 is False, "Terceiro pedido não deveria ser criado (idempotente)"
        
        assert pedido1.id == pedido2.id == pedido3.id, "Todos devem retornar o mesmo pedido"
        
        pedidos_com_chave = Pedido.objects.filter(chave_idempotencia=chave).count()
        assert pedidos_com_chave == 1, f"Deveria existir apenas 1 pedido, mas existem {pedidos_com_chave}"
        
        produto_com_estoque.refresh_from_db()
        estoque_esperado = estoque_inicial - 2
        assert produto_com_estoque.quantidade_estoque == estoque_esperado, \
            f"Estoque deveria ser {estoque_esperado}, mas é {produto_com_estoque.quantidade_estoque}"


@pytest.mark.django_db
class TestAtomicidadeFalhaParcial:
    def test_falha_parcial_nao_altera_estoque(self, cliente_ativo, varios_produtos_com_estoque):
        from produtos.models import Produto
        from pedidos.models import Pedido
        
        produto1, produto2, produto3 = varios_produtos_com_estoque
        
        estoque1_inicial = produto1.quantidade_estoque
        estoque2_inicial = produto2.quantidade_estoque
        estoque3_inicial = produto3.quantidade_estoque
        
        produto3.quantidade_estoque = 0
        produto3.save()
        
        service = CriarPedidoService()
        
        with pytest.raises(EstoqueInsuficienteError):
            service.executar(
                cliente_id=cliente_ativo.id,
                itens=[
                    {'produto_id': produto1.id, 'quantidade': 2},
                    {'produto_id': produto2.id, 'quantidade': 2},
                    {'produto_id': produto3.id, 'quantidade': 2},  # Vai falhar
                ],
                chave_idempotencia='atomicidade-teste-001'
            )
        
        produto1.refresh_from_db()
        produto2.refresh_from_db()
        produto3.refresh_from_db()
        
        assert produto1.quantidade_estoque == estoque1_inicial, \
            f"Estoque produto 1 deveria ser {estoque1_inicial}, mas é {produto1.quantidade_estoque}"
        assert produto2.quantidade_estoque == estoque2_inicial, \
            f"Estoque produto 2 deveria ser {estoque2_inicial}, mas é {produto2.quantidade_estoque}"
        assert produto3.quantidade_estoque == 0, \
            f"Estoque produto 3 deveria ser 0, mas é {produto3.quantidade_estoque}"
        
        pedidos_criados = Pedido.objects.filter(chave_idempotencia='atomicidade-teste-001').count()
        assert pedidos_criados == 0, f"Nenhum pedido deveria existir, mas existem {pedidos_criados}"
