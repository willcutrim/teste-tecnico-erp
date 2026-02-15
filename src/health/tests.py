import pytest


@pytest.mark.django_db
class TestHealthEndpoint:
    """Testes para o endpoint de health check."""
    
    def test_health_endpoint_returns_200(self, api_client):
        response = api_client.get('/health/')
        
        assert response.status_code in [200, 503]
        assert 'status' in response.json()
        assert 'database' in response.json()
        assert 'cache' in response.json()
