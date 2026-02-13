from rest_framework import serializers
from .models import Pedido, ItemPedido, HistoricoStatusPedido


class ItemPedidoSerializer(serializers.ModelSerializer):
    produto_nome = serializers.CharField(source='produto.nome', read_only=True)
    
    class Meta:
        model = ItemPedido
        fields = ['id', 'produto', 'produto_nome', 'quantidade', 'preco_unitario', 'subtotal',]
        read_only_fields = ['id', 'preco_unitario', 'subtotal']


class HistoricoStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = HistoricoStatusPedido
        fields = ['id', 'status_anterior', 'status_novo', 'alterado_por', 'created_at',]


class PedidoListSerializer(serializers.ModelSerializer):
    cliente_nome = serializers.CharField(source='cliente.nome', read_only=True)
    
    class Meta:
        model = Pedido
        fields = ['id', 'numero', 'cliente', 'cliente_nome', 'status', 'valor_total', 'created_at',]


class PedidoDetailSerializer(serializers.ModelSerializer):
    cliente_nome = serializers.CharField(source='cliente.nome', read_only=True)
    itens = ItemPedidoSerializer(many=True, read_only=True)
    historico = HistoricoStatusSerializer(many=True, read_only=True)
    
    class Meta:
        model = Pedido
        fields = [
            'id', 'numero', 'cliente', 'cliente_nome', 'status',
            'valor_total', 'observacoes', 'chave_idempotencia',
            'itens', 'historico', 'created_at', 'updated_at',
        ]


class ItemInputSerializer(serializers.Serializer):
    produto_id = serializers.IntegerField()
    quantidade = serializers.IntegerField(min_value=1)


class CriarPedidoSerializer(serializers.Serializer):
    cliente_id = serializers.IntegerField()
    itens = ItemInputSerializer(many=True)
    idempotency_key = serializers.CharField(max_length=100)
    observacoes = serializers.CharField(required=False, allow_blank=True)


class AlterarStatusSerializer(serializers.Serializer):
    status = serializers.CharField()
