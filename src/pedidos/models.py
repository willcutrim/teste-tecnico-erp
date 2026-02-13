from django.db import models
from django.core.validators import MinValueValidator
from django.conf import settings
from decimal import Decimal
import uuid
from common.models import TimestampMixin, SoftDeleteMixin, SoftDeleteManager


class StatusPedido(models.TextChoices):
    """Status possíveis de um pedido."""
    PENDENTE = 'pendente', 'Pendente'
    CONFIRMADO = 'confirmado', 'Confirmado'
    EM_PROCESSAMENTO = 'em_processamento', 'Em Processamento'
    ENVIADO = 'enviado', 'Enviado'
    ENTREGUE = 'entregue', 'Entregue'
    CANCELADO = 'cancelado', 'Cancelado'


class PedidoManager(SoftDeleteManager):
    def pendentes(self):
        return self.get_queryset().filter(status=StatusPedido.PENDENTE)
    
    def em_andamento(self):
        return self.get_queryset().exclude(
            status__in=[StatusPedido.ENTREGUE, StatusPedido.CANCELADO]
        )


class Pedido(TimestampMixin, SoftDeleteMixin):
    numero = models.CharField('Número', max_length=30, unique=True, db_index=True, editable=False, 
                              help_text='Número único do pedido (gerado automaticamente)'
    )
    cliente = models.ForeignKey('clientes.Cliente', on_delete=models.PROTECT, related_name='pedidos', 
                                verbose_name='Cliente'
    )
    
    status = models.CharField('Status', max_length=20, choices=StatusPedido.choices, default=StatusPedido.PENDENTE,
                              db_index=True
    )
    valor_total = models.DecimalField('Valor Total', max_digits=12, decimal_places=2, default=Decimal('0.00'),
                                      validators=[MinValueValidator(Decimal('0.00'))]
    )
    observacoes = models.TextField('Observações', blank=True, null=True)
    chave_idempotencia = models.CharField('Chave de Idempotência', max_length=255, db_index=True, 
                                          help_text='Chave única para evitar pedidos duplicados'
    )
    
    objects = PedidoManager()
    all_objects = models.Manager()
    
    class Meta:
        db_table = 'pedidos'
        verbose_name = 'Pedido'
        verbose_name_plural = 'Pedidos'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['cliente', 'status'], name='idx_pedido_cliente_status'),
            models.Index(fields=['status', 'created_at'], name='idx_pedido_status_created'),
            models.Index(fields=['numero'], name='idx_pedido_numero'),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(valor_total__gte=Decimal('0.00')),
                name='pedido_valor_total_positivo'
            ),
        ]
    
    def __str__(self):
        return f'Pedido {self.numero}'
    
    def save(self, *args, **kwargs):
        if not self.numero:
            self.numero = self._gerar_numero()
        super().save(*args, **kwargs)
    
    def _gerar_numero(self):
        from django.utils import timezone
        timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
        unique_id = uuid.uuid4().hex[:6].upper()
        return f'PED-{timestamp}-{unique_id}'
    
    def calcular_total(self):
        total = self.itens.aggregate(
            total=models.Sum('subtotal')
        )['total'] or Decimal('0.00')
        self.valor_total = total
        return total


class ItemPedido(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='itens', verbose_name='Pedido')
    produto = models.ForeignKey('produtos.Produto', on_delete=models.PROTECT, related_name='itens_pedido',
                                verbose_name='Produto'
    )
    quantidade = models.PositiveIntegerField('Quantidade', validators=[MinValueValidator(1)])
    preco_unitario = models.DecimalField('Preço Unitário', max_digits=10, decimal_places=2, 
                                         validators=[MinValueValidator(Decimal('0.01'))],
                                         help_text='Preço do produto no momento da compra'
    )
    subtotal = models.DecimalField('Subtotal', max_digits=12, decimal_places=2, 
                                   validators=[MinValueValidator(Decimal('0.01'))]
    )
    
    class Meta:
        db_table = 'itens_pedido'
        verbose_name = 'Item do Pedido'
        verbose_name_plural = 'Itens do Pedido'
        indexes = [
            models.Index(fields=['pedido', 'produto'], name='idx_item_pedido_produto'),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['pedido', 'produto'],
                name='unique_item_pedido_produto'
            ),
            models.CheckConstraint(
                check=models.Q(quantidade__gte=1),
                name='item_quantidade_minima'
            ),
            models.CheckConstraint(
                check=models.Q(subtotal__gte=Decimal('0.01')),
                name='item_subtotal_positivo'
            ),
        ]
    
    def __str__(self):
        return f'{self.quantidade}x {self.produto.nome} - Pedido {self.pedido.numero}'
    
    def save(self, *args, **kwargs):
        self.subtotal = self.quantidade * self.preco_unitario
        super().save(*args, **kwargs)


class HistoricoStatusPedido(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='historico_status', verbose_name='Pedido')
    status_anterior = models.CharField('Status Anterior', max_length=20, choices=StatusPedido.choices, null=True, 
                                       blank=True
    )
    status_novo = models.CharField('Status Novo', max_length=20, choices=StatusPedido.choices)
    alterado_por = models.CharField('Alterado Por', max_length=255, blank=True, null=True, 
                                    help_text='Usuário ou sistema que realizou a alteração'
    )
    created_at = models.DateTimeField('Data da Alteração', auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = 'historico_status_pedido'
        verbose_name = 'Histórico de Status'
        verbose_name_plural = 'Históricos de Status'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['pedido', 'created_at'], name='idx_historico_pedido_data'),
        ]
    
    def __str__(self):
        return f'{self.pedido.numero}: {self.status_anterior} -> {self.status_novo}'
