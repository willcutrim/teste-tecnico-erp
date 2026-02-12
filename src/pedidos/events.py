"""
Eventos do app Pedidos.

Estrutura para emissão de eventos relacionados a pedidos.
"""
from enum import Enum
from typing import Any, Dict


class EventoPedido(str, Enum):
    """Tipos de eventos de pedido."""
    PEDIDO_CRIADO = 'pedido.criado'
    PEDIDO_CONFIRMADO = 'pedido.confirmado'
    PEDIDO_EM_PROCESSAMENTO = 'pedido.em_processamento'
    PEDIDO_ENVIADO = 'pedido.enviado'
    PEDIDO_ENTREGUE = 'pedido.entregue'
    PEDIDO_CANCELADO = 'pedido.cancelado'


def emitir_evento(evento: EventoPedido, payload: Dict[str, Any]) -> None:
    """
    Emite um evento de pedido.
    
    Placeholder para implementação futura com Redis pub/sub, Celery, etc.
    
    Args:
        evento: Tipo do evento
        payload: Dados do evento
    """
    # TODO: Implementar emissão de eventos (Redis pub/sub, Celery, etc.)
    pass
