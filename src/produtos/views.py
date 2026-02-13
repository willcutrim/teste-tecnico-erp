"""
Views do app Produtos.
"""
from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Produto
from .serializers import ProdutoSerializer, EstoqueSerializer


class ProdutoViewSet(
    mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin,
    viewsets.GenericViewSet
):
    queryset = Produto.objects.all()
    serializer_class = ProdutoSerializer
    
    filterset_fields = ['ativo', 'sku']
    
    ordering_fields = ['preco', 'created_at']
    ordering = ['-created_at']
    
    @action(detail=True, methods=['patch'], url_path='stock')
    def stock(self, request, pk=None):
        produto = self.get_object()
        
        serializer = EstoqueSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        produto.quantidade_estoque = serializer.validated_data['quantidade']
        produto.save(update_fields=['quantidade_estoque', 'updated_at'])
        
        return Response(
            ProdutoSerializer(produto).data,
            status=status.HTTP_200_OK
        )
