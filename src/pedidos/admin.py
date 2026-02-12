from django.contrib import admin
from .models import Pedido, ItemPedido, HistoricoStatusPedido


class ItemPedidoInline(admin.TabularInline):
    model = ItemPedido
    extra = 0
    readonly_fields = ['subtotal']


class HistoricoStatusPedidoInline(admin.TabularInline):
    model = HistoricoStatusPedido
    extra = 0
    readonly_fields = ['status_anterior', 'status_novo', 'alterado_por', 'created_at']
    can_delete = False


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ['id', 'numero', 'cliente', 'status', 'valor_total', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['numero', 'cliente__nome', 'cliente__cpf_cnpj']
    readonly_fields = ['numero', 'chave_idempotencia', 'valor_total', 'created_at', 'updated_at']
    inlines = [ItemPedidoInline, HistoricoStatusPedidoInline]
    ordering = ['-created_at']


@admin.register(ItemPedido)
class ItemPedidoAdmin(admin.ModelAdmin):
    list_display = ['id', 'pedido', 'produto', 'quantidade', 'preco_unitario', 'subtotal']
    list_filter = ['pedido__status']
    search_fields = ['pedido__numero', 'produto__nome', 'produto__sku']


@admin.register(HistoricoStatusPedido)
class HistoricoStatusPedidoAdmin(admin.ModelAdmin):
    list_display = ['id', 'pedido', 'status_anterior', 'status_novo', 'alterado_por', 'created_at']
    list_filter = ['status_novo', 'created_at']
    search_fields = ['pedido__numero']
    readonly_fields = ['pedido', 'status_anterior', 'status_novo', 'alterado_por', 'created_at']
