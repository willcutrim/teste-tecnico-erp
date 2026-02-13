from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from common.models import TimestampMixin, SoftDeleteMixin, SoftDeleteManager


class ProdutoManager(SoftDeleteManager):
    def ativos(self):
        return self.get_queryset().filter(ativo=True)
    
    def com_estoque(self):
        return self.get_queryset().filter(quantidade_estoque__gt=0)


class Produto(TimestampMixin, SoftDeleteMixin):
    sku = models.CharField('SKU', max_length=50, unique=True, db_index=True, 
                           help_text='Código único do produto (Stock Keeping Unit)'
    )
    nome = models.CharField('Nome', max_length=255, db_index=True)
    descricao = models.TextField('Descrição', blank=True, null=True)
    preco = models.DecimalField('Preço', max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))],
                                help_text='Preço unitário do produto'
    )
    quantidade_estoque = models.PositiveIntegerField('Quantidade em Estoque', default=0, db_index=True)
    ativo = models.BooleanField('Ativo', default=True, db_index=True)
    
    objects = ProdutoManager()
    all_objects = models.Manager()
    
    class Meta:
        db_table = 'produtos'
        verbose_name = 'Produto'
        verbose_name_plural = 'Produtos'
        ordering = ['nome']
        indexes = [
            models.Index(fields=['nome', 'ativo'], name='idx_produto_nome_ativo'),
            models.Index(fields=['sku', 'ativo'], name='idx_produto_sku_ativo'),
            models.Index(fields=['ativo', 'quantidade_estoque'], name='idx_produto_ativo_estoque'),
        ]
    
    def __str__(self):
        return f'{self.sku} - {self.nome}'
    
    @property
    def em_estoque(self):
        return self.quantidade_estoque > 0
    
    def tem_estoque_suficiente(self, quantidade):
        return self.quantidade_estoque >= quantidade
