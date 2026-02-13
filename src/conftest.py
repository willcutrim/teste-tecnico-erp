import pytest
from decimal import Decimal


@pytest.fixture
def api_client():
    """Return a DRF API client."""
    from rest_framework.test import APIClient
    return APIClient()


@pytest.fixture
def cliente_ativo(db):
    from clientes.models import Cliente
    return Cliente.objects.create(
        nome='Cliente Teste',
        cpf_cnpj='12345678901',
        email='cliente@teste.com',
        telefone='11999999999',
        ativo=True
    )


@pytest.fixture
def cliente_inativo(db):
    from clientes.models import Cliente
    return Cliente.objects.create(
        nome='Cliente Inativo',
        cpf_cnpj='98765432101',
        email='inativo@teste.com',
        ativo=False
    )


@pytest.fixture
def produto_com_estoque(db):
    from produtos.models import Produto
    return Produto.objects.create(
        sku='PROD-001',
        nome='Produto Teste',
        descricao='Descrição do produto teste',
        preco=Decimal('100.00'),
        quantidade_estoque=10,
        ativo=True
    )


@pytest.fixture
def produto_sem_estoque(db):
    from produtos.models import Produto
    return Produto.objects.create(
        sku='PROD-002',
        nome='Produto Sem Estoque',
        preco=Decimal('50.00'),
        quantidade_estoque=0,
        ativo=True
    )


@pytest.fixture
def produto_inativo(db):
    from produtos.models import Produto
    return Produto.objects.create(
        sku='PROD-003',
        nome='Produto Inativo',
        preco=Decimal('75.00'),
        quantidade_estoque=100,
        ativo=False
    )


@pytest.fixture
def varios_produtos_com_estoque(db):
    from produtos.models import Produto
    produtos = []
    for i in range(1, 4):
        produto = Produto.objects.create(
            sku=f'MULTI-{i:03d}',
            nome=f'Produto Multi {i}',
            preco=Decimal(f'{i * 10}.00'),
            quantidade_estoque=5,
            ativo=True
        )
        produtos.append(produto)
    return produtos


@pytest.fixture
def pedido_pendente(db, cliente_ativo, produto_com_estoque):
    from pedidos.models import Pedido, ItemPedido, StatusPedido
    from decimal import Decimal
    
    pedido = Pedido.objects.create(
        cliente=cliente_ativo,
        status=StatusPedido.PENDENTE,
        valor_total=Decimal('200.00'),
        chave_idempotencia='pedido-teste-001'
    )
    
    ItemPedido.objects.create(
        pedido=pedido,
        produto=produto_com_estoque,
        quantidade=2,
        preco_unitario=produto_com_estoque.preco,
        subtotal=Decimal('200.00')
    )
    
    return pedido
