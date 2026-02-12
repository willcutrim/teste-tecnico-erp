from enum import Enum


class StatusPedido(str, Enum):
    """Status possíveis de um pedido."""
    PENDENTE = 'pendente'
    CONFIRMADO = 'confirmado'
    EM_PROCESSAMENTO = 'em_processamento'
    ENVIADO = 'enviado'
    ENTREGUE = 'entregue'
    CANCELADO = 'cancelado'


class TransicaoInvalidaError(Exception):
    """
    Exceção lançada quando uma transição de status é inválida.
    
    Attributes:
        status_atual: Status atual do pedido
        status_novo: Status para o qual tentou transicionar
        transicoes_permitidas: Lista de transições válidas a partir do status atual
    """
    
    def __init__(self, status_atual, status_novo, transicoes_permitidas=None):
        self.status_atual = str(status_atual.value if hasattr(status_atual, 'value') else status_atual)
        self.status_novo = str(status_novo.value if hasattr(status_novo, 'value') else status_novo)
        self.transicoes_permitidas = [
            str(s.value if hasattr(s, 'value') else s) for s in (transicoes_permitidas or [])
        ]
        
        mensagem = (
            f"Transição inválida: não é possível mudar de "
            f"'{self.status_atual}' para '{self.status_novo}'."
        )
        if self.transicoes_permitidas:
            permitidas = ', '.join(self.transicoes_permitidas)
            mensagem += f" Transições permitidas: [{permitidas}]"
        
        super().__init__(mensagem)


TRANSICOES = {
    StatusPedido.PENDENTE: [
        StatusPedido.CONFIRMADO,
        StatusPedido.CANCELADO,
    ],
    StatusPedido.CONFIRMADO: [
        StatusPedido.EM_PROCESSAMENTO,
        StatusPedido.CANCELADO,
    ],
    StatusPedido.EM_PROCESSAMENTO: [
        StatusPedido.ENVIADO,
        StatusPedido.CANCELADO,
    ],
    StatusPedido.ENVIADO: [
        StatusPedido.ENTREGUE,
    ],
    StatusPedido.ENTREGUE: [],
    StatusPedido.CANCELADO: [],
}


class PedidoStateMachine:
    """
    Máquina de estados para gerenciar transições de status de pedidos.
    
    Exemplo de uso:
        pedido = Pedido.objects.get(id=1)
        sm = PedidoStateMachine(pedido.status)
        
        # Verificar se transição é válida
        if sm.pode_transicionar(StatusPedido.CONFIRMADO):
            sm.validar(StatusPedido.CONFIRMADO)
            pedido.status = StatusPedido.CONFIRMADO
            pedido.save()
    """
    
    def __init__(self, status_atual):
        """Inicializa a máquina de estados."""
        self.status_atual = status_atual
    
    def obter_transicoes_permitidas(self):
        """Retorna a lista de status para os quais é possível transicionar."""
        return TRANSICOES.get(self.status_atual, [])
    
    def pode_transicionar(self, status_novo):
        """Verifica se a transição para o novo status é válida."""
        transicoes_permitidas = self.obter_transicoes_permitidas()
        return status_novo in transicoes_permitidas
    
    def validar(self, status_novo):
        """Valida a transição. Lança TransicaoInvalidaError se inválida."""
        if not self.pode_transicionar(status_novo):
            raise TransicaoInvalidaError(
                status_atual=self.status_atual,
                status_novo=status_novo,
                transicoes_permitidas=self.obter_transicoes_permitidas()
            )
    
    def eh_status_final(self):
        """Verifica se o status atual é final (sem transições possíveis)."""
        return len(self.obter_transicoes_permitidas()) == 0
    
    def pode_cancelar(self):
        """Verifica se o pedido pode ser cancelado a partir do status atual."""
        return StatusPedido.CANCELADO in self.obter_transicoes_permitidas()
