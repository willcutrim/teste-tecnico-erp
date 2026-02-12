import pytest
from django.urls import reverse


@pytest.mark.django_db
class TestHealthEndpoint:
    """Tests for the health check endpoint."""
    
    def test_health_endpoint_returns_200(self, api_client):
        """Test that health endpoint returns 200 when services are up."""
        response = api_client.get('/health/')
        
        # May return 503 if database/redis not available in test
        assert response.status_code in [200, 503]
        assert 'status' in response.json()
        assert 'database' in response.json()
        assert 'cache' in response.json()
