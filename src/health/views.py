from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.db import connection
from django.core.cache import cache


@api_view(['GET'])
def health_check(request):
    """
    Health check endpoint.
    Returns status of the application and its dependencies.
    """
    health_status = {
        'status': 'healthy',
        'database': 'healthy',
        'cache': 'healthy',
    }
    
    # Check database connection
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
    except Exception as e:
        health_status['database'] = 'unhealthy'
        health_status['database_error'] = str(e)
        health_status['status'] = 'unhealthy'
    
    # Check Redis connection
    try:
        cache.set('health_check', 'ok', 10)
        if cache.get('health_check') != 'ok':
            raise Exception('Cache read/write failed')
    except Exception as e:
        health_status['cache'] = 'unhealthy'
        health_status['cache_error'] = str(e)
        health_status['status'] = 'unhealthy'
    
    status_code = status.HTTP_200_OK if health_status['status'] == 'healthy' else status.HTTP_503_SERVICE_UNAVAILABLE
    
    return Response(health_status, status=status_code)
