from django.contrib import admin
from .models import Produto


@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = ['id', 'sku', 'nome', 'preco', 'quantidade_estoque', 'ativo', 'created_at']
    list_filter = ['ativo', 'created_at']
    search_fields = ['sku', 'nome', 'descricao']
    ordering = ['-created_at']
