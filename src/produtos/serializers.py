from rest_framework import serializers
from .models import Produto


class ProdutoSerializer(serializers.ModelSerializer):
    """Serializer para Produto."""
    
    class Meta:
        model = Produto
        fields = [
            'id', 'sku', 'nome', 'descricao', 'preco', 'quantidade_estoque', 'ativo', 
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'quantidade_estoque', 'created_at', 'updated_at']


class EstoqueSerializer(serializers.Serializer):
    """Serializer para atualização de estoque."""
    quantidade = serializers.IntegerField(min_value=0)
