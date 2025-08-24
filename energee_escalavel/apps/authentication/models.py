"""
Modelos de autenticação e autorização multi-tenant
"""
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.core.validators import RegexValidator
import uuid
import pyotp
import qrcode
from io import BytesIO
import base64


class User(AbstractUser):
    """
    Modelo de usuário customizado
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField('Email', unique=True)
    phone = models.CharField(
        'Telefone',
        max_length=20,
        validators=[RegexValidator(r'^\+?1?\d{9,15}$')],
        blank=True
    )
    
    # Campos de profile
    full_name = models.CharField('Nome Completo', max_length=150, blank=True)
    avatar = models.ImageField('Avatar', upload_to='avatars/', blank=True, null=True)
    birth_date = models.DateField('Data de Nascimento', blank=True, null=True)
    
    # Campos de auditoria
    email_verified = models.BooleanField('Email Verificado', default=False)
    phone_verified = models.BooleanField('Telefone Verificado', default=False)
    terms_accepted = models.BooleanField('Termos Aceitos', default=False)
    terms_accepted_at = models.DateTimeField('Termos Aceitos em', blank=True, null=True)
    
    # 2FA
    two_factor_enabled = models.BooleanField('2FA Habilitado', default=False)
    totp_secret = models.CharField('Segredo TOTP', max_length=32, blank=True)
    backup_codes = models.JSONField('Códigos de Backup', default=list, blank=True)
    
    # Controle de acesso
    last_login_ip = models.GenericIPAddressField('Último IP de Login', blank=True, null=True)
    failed_login_attempts = models.PositiveIntegerField('Tentativas de Login Falhadas', default=0)
    locked_until = models.DateTimeField('Bloqueado até', blank=True, null=True)
    
    # Campos de timestamp
    created_at = models.DateTimeField('Criado em', auto_now_add=True)
    updated_at = models.DateTimeField('Atualizado em', auto_now=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    class Meta:
        verbose_name = 'Usuário'
        verbose_name_plural = 'Usuários'
        
    def __str__(self):
        return self.email
    
    def get_full_name(self):
        return self.full_name or f"{self.first_name} {self.last_name}".strip() or self.email
    
    @property
    def is_locked(self):
        """Verifica se a conta está bloqueada"""
        return self.locked_until and self.locked_until > timezone.now()
    
    def lock_account(self, minutes=30):
        """Bloqueia a conta por X minutos"""
        self.locked_until = timezone.now() + timezone.timedelta(minutes=minutes)
        self.save(update_fields=['locked_until'])
    
    def unlock_account(self):
        """Desbloqueia a conta"""
        self.locked_until = None
        self.failed_login_attempts = 0
        self.save(update_fields=['locked_until', 'failed_login_attempts'])
    
    def increment_failed_login(self):
        """Incrementa tentativas de login falhadas"""
        self.failed_login_attempts += 1
        
        # Bloqueia após 5 tentativas falhadas
        if self.failed_login_attempts >= 5:
            self.lock_account()
        
        self.save(update_fields=['failed_login_attempts'])
    
    def reset_failed_login(self):
        """Reseta tentativas de login falhadas"""
        self.failed_login_attempts = 0
        self.save(update_fields=['failed_login_attempts'])
    
    def generate_totp_secret(self):
        """Gera segredo TOTP para 2FA"""
        if not self.totp_secret:
            self.totp_secret = pyotp.random_base32()
            self.save(update_fields=['totp_secret'])
        return self.totp_secret
    
    def get_totp_uri(self):
        """Retorna URI para configuração do TOTP"""
        if not self.totp_secret:
            self.generate_totp_secret()
        
        return pyotp.totp.TOTP(self.totp_secret).provisioning_uri(
            name=self.email,
            issuer_name="Energee System"
        )
    
    def get_qr_code(self):
        """Gera QR Code para configuração do 2FA"""
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(self.get_totp_uri())
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        return base64.b64encode(buffer.getvalue()).decode()
    
    def verify_totp(self, token):
        """Verifica token TOTP"""
        if not self.totp_secret:
            return False
        
        totp = pyotp.TOTP(self.totp_secret)
        return totp.verify(token, valid_window=1)
    
    def generate_backup_codes(self, count=10):
        """Gera códigos de backup para 2FA"""
        import secrets
        import string
        
        codes = []
        for _ in range(count):
            code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
            codes.append(code)
        
        self.backup_codes = codes
        self.save(update_fields=['backup_codes'])
        return codes
    
    def use_backup_code(self, code):
        """Usa um código de backup"""
        if code in self.backup_codes:
            self.backup_codes.remove(code)
            self.save(update_fields=['backup_codes'])
            return True
        return False


class Role(models.Model):
    """
    Papéis/Roles do sistema
    """
    ROLE_CHOICES = [
        ('administrador', 'Administrador'),
        ('cliente', 'Cliente'),
        ('parceiro', 'Parceiro'),
        ('gerador', 'Gerador'),
        ('unidade_consumidora', 'Unidade Consumidora'),
    ]
    
    name = models.CharField('Nome', max_length=50, choices=ROLE_CHOICES, unique=True)
    description = models.TextField('Descrição', blank=True)
    permissions = models.JSONField('Permissões', default=dict)
    is_active = models.BooleanField('Ativo', default=True)
    
    # Auditoria
    created_at = models.DateTimeField('Criado em', auto_now_add=True)
    updated_at = models.DateTimeField('Atualizado em', auto_now=True)
    
    class Meta:
        verbose_name = 'Papel'
        verbose_name_plural = 'Papéis'
    
    def __str__(self):
        return self.get_name_display()


class UserRole(models.Model):
    """
    Associação User-Role-Distribuidora (Multi-tenant)
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Usuário')
    role = models.ForeignKey(Role, on_delete=models.CASCADE, verbose_name='Papel')
    distribuidora = models.ForeignKey(
        'distribuidoras.Distribuidora',
        on_delete=models.CASCADE,
        verbose_name='Distribuidora'
    )
    
    # Controle de acesso
    is_active = models.BooleanField('Ativo', default=True)
    permissions_override = models.JSONField('Permissões Extras', default=dict, blank=True)
    
    # Auditoria
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_roles',
        verbose_name='Atribuído por'
    )
    assigned_at = models.DateTimeField('Atribuído em', auto_now_add=True)
    revoked_at = models.DateTimeField('Revogado em', blank=True, null=True)
    
    class Meta:
        verbose_name = 'Papel do Usuário'
        verbose_name_plural = 'Papéis dos Usuários'
        unique_together = ['user', 'role', 'distribuidora']
    
    def __str__(self):
        return f"{self.user.email} - {self.role.name} @ {self.distribuidora.nome}"
    
    def revoke(self, revoked_by=None):
        """Revoga o papel do usuário"""
        self.is_active = False
        self.revoked_at = timezone.now()
        self.save(update_fields=['is_active', 'revoked_at'])


class LoginAttempt(models.Model):
    """
    Log de tentativas de login
    """
    STATUS_CHOICES = [
        ('success', 'Sucesso'),
        ('failed', 'Falhou'),
        ('blocked', 'Bloqueado'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name='Usuário'
    )
    email = models.EmailField('Email Tentativa')
    ip_address = models.GenericIPAddressField('Endereço IP')
    user_agent = models.TextField('User Agent', blank=True)
    status = models.CharField('Status', max_length=20, choices=STATUS_CHOICES)
    failure_reason = models.CharField('Motivo da Falha', max_length=100, blank=True)
    
    # Informações de localização (opcional)
    country = models.CharField('País', max_length=100, blank=True)
    city = models.CharField('Cidade', max_length=100, blank=True)
    
    # Timestamp
    attempted_at = models.DateTimeField('Tentativa em', auto_now_add=True)
    
    class Meta:
        verbose_name = 'Tentativa de Login'
        verbose_name_plural = 'Tentativas de Login'
        ordering = ['-attempted_at']
    
    def __str__(self):
        return f"{self.email} - {self.status} - {self.attempted_at}"


class PasswordResetToken(models.Model):
    """
    Tokens para reset de senha
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    used = models.BooleanField('Usado', default=False)
    expires_at = models.DateTimeField('Expira em')
    created_at = models.DateTimeField('Criado em', auto_now_add=True)
    
    class Meta:
        verbose_name = 'Token de Reset de Senha'
        verbose_name_plural = 'Tokens de Reset de Senha'
    
    def __str__(self):
        return f"{self.user.email} - {self.token}"
    
    @property
    def is_expired(self):
        return timezone.now() > self.expires_at
    
    @property
    def is_valid(self):
        return not self.used and not self.is_expired


class UserSession(models.Model):
    """
    Sessões ativas dos usuários
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    session_key = models.CharField('Chave da Sessão', max_length=40, unique=True)
    ip_address = models.GenericIPAddressField('Endereço IP')
    user_agent = models.TextField('User Agent', blank=True)
    
    # Controle de sessão
    is_active = models.BooleanField('Ativa', default=True)
    last_activity = models.DateTimeField('Última Atividade', auto_now=True)
    
    # Timestamps
    created_at = models.DateTimeField('Criada em', auto_now_add=True)
    expires_at = models.DateTimeField('Expira em')
    
    class Meta:
        verbose_name = 'Sessão do Usuário'
        verbose_name_plural = 'Sessões dos Usuários'
        ordering = ['-last_activity']
    
    def __str__(self):
        return f"{self.user.email} - {self.session_key[:8]}..."
    
    @property
    def is_expired(self):
        return timezone.now() > self.expires_at
    
    def terminate(self):
        """Termina a sessão"""
        self.is_active = False
        self.save(update_fields=['is_active'])