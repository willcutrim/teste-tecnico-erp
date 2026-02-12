from rest_framework import viewsets, mixins
from .models import Cliente
from .serializers import ClienteSerializer


class ClienteViewSet(
    mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    queryset = Cliente.objects.all()
    serializer_class = ClienteSerializer
    
    filterset_fields = ['ativo', 'email', 'cpf_cnpj']
    
    ordering_fields = ['created_at', 'nome']
    ordering = ['-created_at']

