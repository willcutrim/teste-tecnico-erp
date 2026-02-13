from django.db import models
from django.core.validators import EmailValidator
from common.models import TimestampMixin, SoftDeleteMixin, SoftDeleteManager


class ClienteManager(SoftDeleteManager):
    """Manager para Cliente com soft delete."""
    pass


class Cliente(TimestampMixin, SoftDeleteMixin):
    nome = models.CharField('Nome', max_length=255,db_index=True)
    cpf_cnpj = models.CharField('CPF/CNPJ', max_length=18, unique=True, db_index=True, 
                                help_text='CPF (11 dígitos) ou CNPJ (14 dígitos)'
    )
    email = models.EmailField('E-mail', max_length=255, unique=True, validators=[EmailValidator()], db_index=True)
    telefone = models.CharField('Telefone', max_length=20, blank=True, null=True)
    endereco = models.TextField('Endereço', blank=True, null=True)
    ativo = models.BooleanField('Ativo', default=True, db_index=True)
    objects = ClienteManager()
    all_objects = models.Manager()
    
    class Meta:
        db_table = 'clientes'
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['nome', 'ativo'], name='idx_cliente_nome_ativo'),
            models.Index(fields=['email', 'ativo'], name='idx_cliente_email_ativo'),
        ]
    
    def __str__(self):
        return f'{self.nome} ({self.cpf_cnpj})'
