from django.db import models
from django.utils import timezone


class SoftDeleteManager(models.Manager):
    """
    Manager que filtra registros soft-deleted por padrão.
    """
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)
    
    def with_deleted(self):
        """Retorna todos os registros, incluindo deletados."""
        return super().get_queryset()
    
    def only_deleted(self):
        """Retorna apenas registros deletados."""
        return super().get_queryset().filter(deleted_at__isnull=False)


class SoftDeleteMixin(models.Model):
    """
    Mixin que adiciona soft delete ao model.
    """
    deleted_at = models.DateTimeField(
        'Deletado em',
        null=True,
        blank=True,
        db_index=True
    )
    
    class Meta:
        abstract = True
    
    def delete(self, using=None, keep_parents=False):
        """Soft delete: marca deleted_at ao invés de deletar."""
        self.deleted_at = timezone.now()
        self.save(update_fields=['deleted_at'])
    
    def hard_delete(self, using=None, keep_parents=False):
        """Delete real do banco de dados."""
        super().delete(using=using, keep_parents=keep_parents)
    
    def restore(self):
        """Restaura um registro soft-deleted."""
        self.deleted_at = None
        self.save(update_fields=['deleted_at'])
    
    @property
    def is_deleted(self):
        return self.deleted_at is not None


class TimestampMixin(models.Model):
    """
    Mixin that adds created_at and updated_at fields.
    """
    created_at = models.DateTimeField('Criado em', auto_now_add=True)
    updated_at = models.DateTimeField('Atualizado em', auto_now=True)

    class Meta:
        abstract = True
