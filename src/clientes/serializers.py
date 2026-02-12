from rest_framework import serializers
from .models import Cliente


class ClienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cliente
        fields = [
            'id', 'nome', 'cpf_cnpj', 'email', 'telefone', 'endereco', 'ativo', 'created_at', 'updated_at',
        ]

        read_only_fields = ['id', 'created_at', 'updated_at']

