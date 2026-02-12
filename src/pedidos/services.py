"""
Services do app Pedidos.
"""
from typing import Optional
from django.db import transaction

from .models import Pedido, HistoricoStatusPedido
from .state_machine import PedidoStateMachine, TransicaoInvalidaError


class PedidoNaoEncontradoError(Exception):
    """Exceção lançada quando o pedido não é encontrado."""
    pass


class AlterarStatusPedidoService:
    """
    Serviço responsável por alterar o status de um pedido.
    
    Garante:
    - Atomicidade da operação
    - Lock pessimista para evitar race conditions
    - Validação de transição via state machine
    - Registro de histórico de alterações
    
    Exemplo de uso:
        service = AlterarStatusPedidoService()
        pedido = service.executar(
            pedido_id=1,
            novo_status='confirmado',
            alterado_por='usuario@email.com'
        )
    """
    
    @transaction.atomic
    def executar(
        self,
        pedido_id: int,
        novo_status: str,
        alterado_por: Optional[str] = None
    ) -> Pedido:
        """
        Altera o status de um pedido.
        
        Args:
            pedido_id: ID do pedido
            novo_status: Novo status desejado
            alterado_por: Identificação de quem está alterando (usuário ou sistema)
            
        Returns:
            Pedido atualizado
            
        Raises:
            PedidoNaoEncontradoError: Se o pedido não existir
            TransicaoInvalidaError: Se a transição de status não for válida
        """
        # Busca pedido com lock para evitar race conditions
        pedido = self._obter_pedido_com_lock(pedido_id)
        
        # Guarda status anterior
        status_anterior = pedido.status
        
        # Valida transição usando state machine
        state_machine = PedidoStateMachine(status_anterior)
        state_machine.validar(novo_status)
        
        # Atualiza status do pedido
        pedido.status = novo_status
        pedido.save(update_fields=['status', 'updated_at'])
        
        # Registra histórico
        self._registrar_historico(
            pedido=pedido,
            status_anterior=status_anterior,
            status_novo=novo_status,
            alterado_por=alterado_por
        )
        
        return pedido
    
    def _obter_pedido_com_lock(self, pedido_id: int) -> Pedido:
        """
        Obtém o pedido com lock pessimista.
        
        Args:
            pedido_id: ID do pedido
            
        Returns:
            Pedido com lock
            
        Raises:
            PedidoNaoEncontradoError: Se o pedido não existir
        """
        try:
            return Pedido.objects.select_for_update().get(id=pedido_id)
        except Pedido.DoesNotExist:
            raise PedidoNaoEncontradoError(
                f"Pedido com ID {pedido_id} não encontrado"
            )
    
    def _registrar_historico(
        self,
        pedido: Pedido,
        status_anterior: str,
        status_novo: str,
        alterado_por: Optional[str]
    ) -> HistoricoStatusPedido:
        """
        Registra a alteração de status no histórico.
        
        Args:
            pedido: Pedido alterado
            status_anterior: Status antes da alteração
            status_novo: Novo status
            alterado_por: Quem realizou a alteração
            
        Returns:
            Registro de histórico criado
        """
        return HistoricoStatusPedido.objects.create(
            pedido=pedido,
            status_anterior=status_anterior,
            status_novo=status_novo,
            alterado_por=alterado_por
        )

