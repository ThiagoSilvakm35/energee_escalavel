"""
Modelo da Distribuidora - Tenant principal do sistema multi-tenant
"""
from django.db import models
from django.core.validators import RegexValidator, EmailValidator
from django.utils.text import slugify
from apps.core.models import BaseModel
import uuid


class Distribuidora(BaseModel):
    """
    Distribuidora de Energia Elétrica - Tenant principal
    """
    STATUS_CHOICES = [
        ('ativo', 'Ativo'),
        ('inativo', 'Inativo'),
        ('suspenso', 'Suspenso'),
        ('em_manutencao', 'Em Manutenção'),
    ]
    
    # Dados principais
    nome = models.CharField('Nome', max_length=200)
    razao_social = models.CharField('Razão Social', max_length=200)
    nome_fantasia = models.CharField('Nome Fantasia', max_length=200, blank=True)
    slug = models.SlugField('Slug', max_length=100, unique=True, help_text='URL amigável')
    
    # Documentos
    cnpj = models.CharField(
        'CNPJ',
        max_length=18,
        unique=True,
        validators=[RegexValidator(r'^\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}$')]
    )
    inscricao_estadual = models.CharField('Inscrição Estadual', max_length=20, blank=True)
    codigo_aneel = models.CharField('Código ANEEL', max_length=10, unique=True)
    
    # Endereço
    endereco = models.CharField('Endereço', max_length=300)
    numero = models.CharField('Número', max_length=10)
    complemento = models.CharField('Complemento', max_length=100, blank=True)
    bairro = models.CharField('Bairro', max_length=100)
    cidade = models.CharField('Cidade', max_length=100)
    estado = models.CharField('Estado', max_length=2)
    cep = models.CharField(
        'CEP',
        max_length=10,
        validators=[RegexValidator(r'^\d{5}-?\d{3}$')]
    )
    
    # Contato
    telefone = models.CharField(
        'Telefone',
        max_length=20,
        validators=[RegexValidator(r'^\+?1?\d{9,15}$')]
    )
    email = models.EmailField('Email', validators=[EmailValidator()])
    website = models.URLField('Website', blank=True)
    
    # Configurações operacionais
    status = models.CharField('Status', max_length=20, choices=STATUS_CHOICES, default='ativo')
    area_concessao = models.TextField('Área de Concessão', help_text='Municípios atendidos')
    tarifa_media = models.DecimalField('Tarifa Média (R$/kWh)', max_digits=10, decimal_places=4, default=0)
    
    # Configurações do sistema
    logo = models.ImageField('Logo', upload_to='distribuidoras/logos/', blank=True, null=True)
    cores_tema = models.JSONField('Cores do Tema', default=dict, blank=True)
    configuracoes = models.JSONField('Configurações Gerais', default=dict, blank=True)
    
    # Limites e quotas
    max_usuarios = models.PositiveIntegerField('Máximo de Usuários', default=100)
    max_organizacoes = models.PositiveIntegerField('Máximo de Organizações', default=50)
    max_usinas = models.PositiveIntegerField('Máximo de Usinas', default=20)
    max_storage_gb = models.PositiveIntegerField('Máximo Storage (GB)', default=10)
    
    # Configurações de faturamento
    dia_vencimento_padrao = models.PositiveIntegerField(
        'Dia Vencimento Padrão',
        default=10,
        help_text='Dia do mês para vencimento das faturas'
    )
    multa_atraso = models.DecimalField('Multa por Atraso (%)', max_digits=5, decimal_places=2, default=2.0)
    juros_mora = models.DecimalField('Juros de Mora (% a.m.)', max_digits=5, decimal_places=2, default=1.0)
    
    # Auditoria
    data_inicio_operacao = models.DateField('Data de Início da Operação', null=True, blank=True)
    ultima_manutencao = models.DateTimeField('Última Manutenção', null=True, blank=True)
    
    class Meta:
        verbose_name = 'Distribuidora'
        verbose_name_plural = 'Distribuidoras'
        ordering = ['nome']
    
    def __str__(self):
        return self.nome
    
    def save(self, *args, **kwargs):
        """
        Override save para gerar slug automaticamente
        """
        if not self.slug:
            self.slug = slugify(self.nome)
        super().save(*args, **kwargs)
    
    @property
    def endereco_completo(self):
        """Retorna endereço formatado"""
        endereco = f"{self.endereco}, {self.numero}"
        if self.complemento:
            endereco += f", {self.complemento}"
        endereco += f" - {self.bairro}, {self.cidade}/{self.estado} - CEP: {self.cep}"
        return endereco
    
    @property
    def is_active(self):
        """Verifica se a distribuidora está ativa"""
        return self.status == 'ativo'
    
    def get_configuracao(self, chave, default=None):
        """Retorna configuração específica"""
        return self.configuracoes.get(chave, default)
    
    def set_configuracao(self, chave, valor):
        """Define configuração específica"""
        if not self.configuracoes:
            self.configuracoes = {}
        self.configuracoes[chave] = valor
        self.save(update_fields=['configuracoes'])
    
    def get_usage_stats(self):
        """Retorna estatísticas de uso"""
        from apps.organizacoes.models import Organizacao
        from apps.usinas.models import Usinas
        from apps.authentication.models import UserRole
        
        return {
            'usuarios_count': UserRole.objects.filter(distribuidora=self, is_active=True).count(),
            'organizacoes_count': Organizacao.objects.filter(distribuidora=self).count(),
            'usinas_count': Usinas.objects.filter(distribuidora=self).count(),
            'max_usuarios': self.max_usuarios,
            'max_organizacoes': self.max_organizacoes,
            'max_usinas': self.max_usinas,
        }
    
    def is_over_limit(self):
        """Verifica se está acima dos limites"""
        stats = self.get_usage_stats()
        return (
            stats['usuarios_count'] > self.max_usuarios or
            stats['organizacoes_count'] > self.max_organizacoes or
            stats['usinas_count'] > self.max_usinas
        )


class DistribuidoraConfig(models.Model):
    """
    Configurações específicas da distribuidora
    """
    distribuidora = models.OneToOneField(
        Distribuidora,
        on_delete=models.CASCADE,
        related_name='config'
    )
    
    # Configurações de email
    smtp_host = models.CharField('SMTP Host', max_length=100, blank=True)
    smtp_port = models.PositiveIntegerField('SMTP Port', default=587)
    smtp_user = models.CharField('SMTP User', max_length=100, blank=True)
    smtp_password = models.CharField('SMTP Password', max_length=100, blank=True)
    smtp_use_tls = models.BooleanField('SMTP Use TLS', default=True)
    
    # Configurações de notificação
    webhook_url = models.URLField('Webhook URL', blank=True)
    slack_webhook = models.URLField('Slack Webhook', blank=True)
    
    # Configurações de backup
    backup_enabled = models.BooleanField('Backup Habilitado', default=True)
    backup_frequency = models.CharField(
        'Frequência de Backup',
        max_length=20,
        choices=[
            ('daily', 'Diário'),
            ('weekly', 'Semanal'),
            ('monthly', 'Mensal'),
        ],
        default='daily'
    )
    backup_retention_days = models.PositiveIntegerField('Retenção Backup (dias)', default=30)
    
    # Configurações de segurança
    force_2fa = models.BooleanField('Forçar 2FA', default=False)
    password_expiry_days = models.PositiveIntegerField('Expiração Senha (dias)', default=90)
    max_session_duration = models.PositiveIntegerField('Duração Máxima Sessão (min)', default=480)
    
    # Configurações de relatórios
    relatorios_automaticos = models.BooleanField('Relatórios Automáticos', default=True)
    formato_relatorio_padrao = models.CharField(
        'Formato Padrão Relatórios',
        max_length=10,
        choices=[
            ('pdf', 'PDF'),
            ('xlsx', 'Excel'),
            ('csv', 'CSV'),
        ],
        default='pdf'
    )
    
    class Meta:
        verbose_name = 'Configuração da Distribuidora'
        verbose_name_plural = 'Configurações das Distribuidoras'
    
    def __str__(self):
        return f"Config - {self.distribuidora.nome}"


class DistribuidoraAuditLog(models.Model):
    """
    Log de auditoria específico da distribuidora
    """
    distribuidora = models.ForeignKey(Distribuidora, on_delete=models.CASCADE)
    user = models.ForeignKey(
        'authentication.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    # Detalhes da ação
    action = models.CharField('Ação', max_length=100)
    object_type = models.CharField('Tipo de Objeto', max_length=100)
    object_id = models.CharField('ID do Objeto', max_length=100)
    changes = models.JSONField('Alterações', default=dict)
    
    # Contexto
    ip_address = models.GenericIPAddressField('IP', null=True, blank=True)
    user_agent = models.TextField('User Agent', blank=True)
    
    # Timestamp
    timestamp = models.DateTimeField('Data/Hora', auto_now_add=True)
    
    class Meta:
        verbose_name = 'Log de Auditoria'
        verbose_name_plural = 'Logs de Auditoria'
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.distribuidora.nome} - {self.action} - {self.timestamp}"