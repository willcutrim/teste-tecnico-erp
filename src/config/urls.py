"""
URL configuration for ERP - Gestão de Pedidos.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', include('health.urls')),
    path('api/clientes/', include('clientes.urls')),
    path('api/produtos/', include('produtos.urls')),
    path('api/pedidos/', include('pedidos.urls')),
]
