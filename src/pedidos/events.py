import logging
from enum import Enum

logger = logging.getLogger(__name__)


class EventoPedido(str, Enum):
    """Tipos de eventos de pedido."""
    PEDIDO_CRIADO = 'pedido.criado'
    PEDIDO_CONFIRMADO = 'pedido.confirmado'
    PEDIDO_EM_PROCESSAMENTO = 'pedido.em_processamento'
    PEDIDO_ENVIADO = 'pedido.enviado'
    PEDIDO_ENTREGUE = 'pedido.entregue'
    PEDIDO_CANCELADO = 'pedido.cancelado'


def emitir_evento(evento, payload):
    """Emite um evento de pedido (loga por enquanto)."""
    logger.info(
        "Evento emitido: %s | Payload: %s",
        evento.value,
        payload
    )
    
    # TODO - Willyam cutrim: Implementar emissão de eventos (Redis pub/sub, Celery, etc.) esquece ñ papai
