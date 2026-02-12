from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Pedido
from .serializers import (
    PedidoListSerializer, PedidoDetailSerializer, CriarPedidoSerializer, AlterarStatusSerializer,
)
from .services import (
    CriarPedidoService, AlterarStatusPedidoService, CancelarPedidoService, ClienteNaoEncontradoError,
    ClienteInativoError, ProdutoNaoEncontradoError, ProdutoInativoError, EstoqueInsuficienteError,
    ItensVaziosError, QuantidadeInvalidaError, PedidoNaoEncontradoError, PedidoNaoPodeCancelarError,
)
from .state_machine import TransicaoInvalidaError


class PedidoViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    queryset = Pedido.objects.all().select_related('cliente')
    
    filterset_fields = ['status', 'cliente']
    
    ordering_fields = ['created_at', 'valor_total', 'status']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return PedidoListSerializer
        return PedidoDetailSerializer
    
    def create(self, request):
        serializer = CriarPedidoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        
        try:
            service = CriarPedidoService()
            pedido, criado = service.executar(
                cliente_id=data['cliente_id'],
                itens=data['itens'],
                chave_idempotencia=data['idempotency_key'],
                observacoes=data.get('observacoes'),
            )
            
            response_status = status.HTTP_201_CREATED if criado else status.HTTP_200_OK
            return Response(
                PedidoDetailSerializer(pedido).data,
                status=response_status
            )
            
        except (ClienteNaoEncontradoError, ProdutoNaoEncontradoError) as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        except (ClienteInativoError, ProdutoInativoError) as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except EstoqueInsuficienteError as e:
            return Response(
                {
                    'error': str(e),
                    'produto_id': e.produto_id,
                    'disponivel': e.disponivel,
                    'solicitado': e.solicitado,
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        except (ItensVaziosError, QuantidadeInvalidaError) as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['patch'], url_path='status')
    def status_action(self, request, pk=None):
        serializer = AlterarStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            service = AlterarStatusPedidoService()
            pedido = service.executar(
                pedido_id=int(pk),
                novo_status=serializer.validated_data['status'],
                alterado_por=request.user.username if request.user.is_authenticated else None,
            )
            
            return Response(
                PedidoDetailSerializer(pedido).data,
                status=status.HTTP_200_OK
            )
            
        except PedidoNaoEncontradoError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        except TransicaoInvalidaError as e:
            return Response(
                {
                    'error': str(e),
                    'status_atual': e.status_atual,
                    'status_novo': e.status_novo,
                    'transicoes_permitidas': e.transicoes_permitidas,
                },
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def destroy(self, request, pk=None):
        try:
            service = CancelarPedidoService()
            pedido = service.executar(
                pedido_id=int(pk),
                cancelado_por=request.user.username if request.user.is_authenticated else None,
                motivo=request.data.get('motivo'),
            )
            
            return Response(
                PedidoDetailSerializer(pedido).data,
                status=status.HTTP_200_OK
            )
            
        except PedidoNaoEncontradoError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        except PedidoNaoPodeCancelarError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
