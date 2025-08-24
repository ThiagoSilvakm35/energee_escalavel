"""
Modelos base para sistema multi-tenant
"""
from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model
import uuid


class TimestampedModel(models.Model):
    """
    Modelo abstrato que adiciona campos de timestamp
    """
    created_at = models.DateTimeField('Criado em', auto_now_add=True)
    updated_at = models.DateTimeField('Atualizado em', auto_now=True)
    
    class Meta:
        abstract = True


class SoftDeleteManager(models.Manager):
    """
    Manager que filtra registros com soft delete
    """
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class SoftDeleteModel(models.Model):
    """
    Modelo abstrato que implementa soft delete
    """
    deleted_at = models.DateTimeField('Deletado em', null=True, blank=True)
    
    objects = SoftDeleteManager()
    all_objects = models.Manager()  # Manager que inclui registros deletados
    
    class Meta:
        abstract = True
    
    def soft_delete(self):
        """
        Soft delete do registro
        """
        self.deleted_at = timezone.now()
        self.save(update_fields=['deleted_at'])
    
    def restore(self):
        """
        Restaura um registro soft deleted
        """
        self.deleted_at = None
        self.save(update_fields=['deleted_at'])
    
    @property
    def is_deleted(self):
        return self.deleted_at is not None


class AuditModel(models.Model):
    """
    Modelo abstrato que adiciona campos de auditoria
    """
    created_by = models.ForeignKey(
        'authentication.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(app_label)s_%(class)s_created',
        verbose_name='Criado por'
    )
    updated_by = models.ForeignKey(
        'authentication.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(app_label)s_%(class)s_updated',
        verbose_name='Atualizado por'
    )
    
    class Meta:
        abstract = True


class BaseModel(TimestampedModel, SoftDeleteModel, AuditModel):
    """
    Modelo base que combina timestamp, soft delete e auditoria
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    class Meta:
        abstract = True


class TenantModel(BaseModel):
    """
    Modelo abstrato para entidades que pertencem a um tenant (Distribuidora)
    """
    distribuidora = models.ForeignKey(
        'distribuidoras.Distribuidora',
        on_delete=models.CASCADE,
        verbose_name='Distribuidora',
        help_text='Distribuidora responsável (Tenant)'
    )
    
    class Meta:
        abstract = True


class CacheConfig(models.Model):
    """
    Configurações de cache por tenant
    """
    distribuidora = models.OneToOneField(
        'distribuidoras.Distribuidora',
        on_delete=models.CASCADE,
        verbose_name='Distribuidora'
    )
    ttl_faturas = models.PositiveIntegerField(
        'TTL Faturas (segundos)',
        default=300,
        help_text='Tempo de vida do cache para faturas'
    )
    ttl_relatorios = models.PositiveIntegerField(
        'TTL Relatórios (segundos)',
        default=3600,
        help_text='Tempo de vida do cache para relatórios'
    )
    ttl_usinas = models.PositiveIntegerField(
        'TTL Usinas (segundos)',
        default=1800,
        help_text='Tempo de vida do cache para usinas'
    )
    max_cache_size = models.PositiveIntegerField(
        'Tamanho máximo do cache (MB)',
        default=100,
        help_text='Tamanho máximo do cache em MB'
    )
    enabled = models.BooleanField('Habilitado', default=True)
    
    class Meta:
        verbose_name = 'Configuração de Cache'
        verbose_name_plural = 'Configurações de Cache'
    
    def __str__(self):
        return f"Cache Config - {self.distribuidora.nome}"


class SystemHealth(models.Model):
    """
    Monitoramento de saúde do sistema
    """
    SERVICE_CHOICES = [
        ('database', 'Database'),
        ('redis', 'Redis'),
        ('celery', 'Celery'),
        ('storage', 'Storage'),
    ]
    
    STATUS_CHOICES = [
        ('healthy', 'Healthy'),
        ('degraded', 'Degraded'),
        ('unhealthy', 'Unhealthy'),
    ]
    
    service = models.CharField('Serviço', max_choices=50, choices=SERVICE_CHOICES)
    status = models.CharField('Status', max_length=20, choices=STATUS_CHOICES)
    response_time = models.FloatField('Tempo de Resposta (ms)', null=True, blank=True)
    error_message = models.TextField('Mensagem de Erro', blank=True)
    checked_at = models.DateTimeField('Verificado em', auto_now_add=True)
    
    class Meta:
        verbose_name = 'Saúde do Sistema'
        verbose_name_plural = 'Saúde do Sistema'
        ordering = ['-checked_at']
    
    def __str__(self):
        return f"{self.service} - {self.status} ({self.checked_at})"