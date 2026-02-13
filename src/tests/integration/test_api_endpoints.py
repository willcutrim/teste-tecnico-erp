import pytest
from decimal import Decimal
from rest_framework import status


@pytest.mark.django_db
class TestClientesAPI:
    def test_criar_cliente(self, api_client):
        payload = {
            'nome': 'Novo Cliente',
            'cpf_cnpj': '12345678901',
            'email': 'novo@cliente.com',
            'telefone': '11999999999',
            'ativo': True
        }
        
        response = api_client.post('/api/v1/customers/', payload, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['nome'] == 'Novo Cliente'
        assert response.data['email'] == 'novo@cliente.com'
        assert 'id' in response.data
    
    def test_listar_clientes(self, api_client, cliente_ativo):
        response = api_client.get('/api/v1/customers/')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data  # Paginação
        assert 'count' in response.data
    
    def test_obter_cliente(self, api_client, cliente_ativo):
        response = api_client.get(f'/api/v1/customers/{cliente_ativo.id}/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == cliente_ativo.id
        assert response.data['nome'] == cliente_ativo.nome


@pytest.mark.django_db
class TestProdutosAPI:
    def test_criar_produto(self, api_client):
        payload = {
            'sku': 'SKU-TESTE-001',
            'nome': 'Produto API',
            'descricao': 'Produto criado via API',
            'preco': '99.99',
            'ativo': True
        }
        
        response = api_client.post('/api/v1/products/', payload, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['sku'] == 'SKU-TESTE-001'
        assert response.data['nome'] == 'Produto API'
    
    def test_listar_produtos(self, api_client, produto_com_estoque):
        response = api_client.get('/api/v1/products/')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data
    
    def test_atualizar_estoque(self, api_client, produto_com_estoque):
        payload = {'quantidade': 50}
        
        response = api_client.patch(
            f'/api/v1/products/{produto_com_estoque.id}/stock/',
            payload,
            format='json'
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['quantidade_estoque'] == 50


@pytest.mark.django_db
class TestPedidosAPI:
    def test_criar_pedido(self, api_client, cliente_ativo, produto_com_estoque):
        payload = {
            'cliente_id': cliente_ativo.id,
            'itens': [
                {'produto_id': produto_com_estoque.id, 'quantidade': 2}
            ],
            'idempotency_key': 'api-teste-001'
        }
        
        response = api_client.post('/api/v1/orders/', payload, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['cliente'] == cliente_ativo.id
        assert response.data['status'] == 'pendente'
        assert 'numero' in response.data
    
    def test_criar_pedido_idempotente(self, api_client, cliente_ativo, produto_com_estoque):
        payload = {
            'cliente_id': cliente_ativo.id,
            'itens': [
                {'produto_id': produto_com_estoque.id, 'quantidade': 1}
            ],
            'idempotency_key': 'api-idempotente-001'
        }
        
        response1 = api_client.post('/api/v1/orders/', payload, format='json')
        assert response1.status_code == status.HTTP_201_CREATED
        
        response2 = api_client.post('/api/v1/orders/', payload, format='json')
        assert response2.status_code == status.HTTP_200_OK
        
        assert response1.data['id'] == response2.data['id']
    
    def test_listar_pedidos(self, api_client, pedido_pendente):
        response = api_client.get('/api/v1/orders/')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data
        assert response.data['count'] >= 1
    
    def test_obter_pedido(self, api_client, pedido_pendente):
        response = api_client.get(f'/api/v1/orders/{pedido_pendente.id}/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == pedido_pendente.id
        assert 'itens' in response.data
        assert 'historico' in response.data
    
    def test_alterar_status(self, api_client, pedido_pendente):
        payload = {'status': 'confirmado'}
        
        response = api_client.patch(
            f'/api/v1/orders/{pedido_pendente.id}/status/',
            payload,
            format='json'
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'confirmado'
    
    def test_alterar_status_transicao_invalida(self, api_client, pedido_pendente):
        payload = {'status': 'enviado'}
        
        response = api_client.patch(
            f'/api/v1/orders/{pedido_pendente.id}/status/',
            payload,
            format='json'
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data
    
    def test_cancelar_pedido(self, api_client, pedido_pendente, produto_com_estoque):
        estoque_antes = produto_com_estoque.quantidade_estoque
        
        response = api_client.delete(f'/api/v1/orders/{pedido_pendente.id}/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'cancelado'
        
        produto_com_estoque.refresh_from_db()
        assert produto_com_estoque.quantidade_estoque == estoque_antes + 2
    
    def test_filtrar_pedidos_por_status(self, api_client, pedido_pendente):
        response = api_client.get('/api/v1/orders/?status=pendente')
        
        assert response.status_code == status.HTTP_200_OK
        for pedido in response.data['results']:
            assert pedido['status'] == 'pendente'
    
    def test_ordenar_pedidos(self, api_client, pedido_pendente):
        response = api_client.get('/api/v1/orders/?ordering=-created_at')
        
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestHealthCheck:
    def test_health_check(self, api_client):
        response = api_client.get('/health/')
        
        assert response.status_code == status.HTTP_200_OK
