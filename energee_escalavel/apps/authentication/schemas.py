"""
Schemas Pydantic para APIs de Autenticação
"""
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
import re


class LoginSchema(BaseModel):
    """Schema para login"""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    

class Login2FASchema(BaseModel):
    """Schema para login com 2FA"""
    temp_token: str
    totp_code: str = Field(..., min_length=6, max_length=8)


class RegisterSchema(BaseModel):
    """Schema para registro de usuário"""
    email: EmailStr
    password: str = Field(..., min_length=12, max_length=128)
    password_confirm: str = Field(..., min_length=12, max_length=128)
    full_name: str = Field(..., min_length=2, max_length=150)
    phone: Optional[str] = Field(None, max_length=20)
    terms_accepted: bool = True
    
    @validator('password')
    def validate_password(cls, v):
        """Valida força da senha"""
        if len(v) < 12:
            raise ValueError('Senha deve ter pelo menos 12 caracteres')
        
        # Pelo menos uma letra maiúscula
        if not re.search(r'[A-Z]', v):
            raise ValueError('Senha deve conter pelo menos uma letra maiúscula')
        
        # Pelo menos uma letra minúscula
        if not re.search(r'[a-z]', v):
            raise ValueError('Senha deve conter pelo menos uma letra minúscula')
        
        # Pelo menos um dígito
        if not re.search(r'\d', v):
            raise ValueError('Senha deve conter pelo menos um número')
        
        # Pelo menos um caractere especial
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Senha deve conter pelo menos um caractere especial')
        
        return v
    
    @validator('password_confirm')
    def passwords_match(cls, v, values):
        """Verifica se as senhas coincidem"""
        if 'password' in values and v != values['password']:
            raise ValueError('Senhas não coincidem')
        return v
    
    @validator('phone')
    def validate_phone(cls, v):
        """Valida formato do telefone"""
        if v and not re.match(r'^\+?1?\d{9,15}$', v):
            raise ValueError('Formato de telefone inválido')
        return v
    
    @validator('terms_accepted')
    def terms_must_be_accepted(cls, v):
        """Verifica se os termos foram aceitos"""
        if not v:
            raise ValueError('Termos de uso devem ser aceitos')
        return v


class ChangePasswordSchema(BaseModel):
    """Schema para alteração de senha"""
    current_password: str
    new_password: str = Field(..., min_length=12, max_length=128)
    new_password_confirm: str = Field(..., min_length=12, max_length=128)
    
    @validator('new_password')
    def validate_new_password(cls, v):
        """Valida força da nova senha"""
        if len(v) < 12:
            raise ValueError('Nova senha deve ter pelo menos 12 caracteres')
        
        if not re.search(r'[A-Z]', v):
            raise ValueError('Nova senha deve conter pelo menos uma letra maiúscula')
        
        if not re.search(r'[a-z]', v):
            raise ValueError('Nova senha deve conter pelo menos uma letra minúscula')
        
        if not re.search(r'\d', v):
            raise ValueError('Nova senha deve conter pelo menos um número')
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Nova senha deve conter pelo menos um caractere especial')
        
        return v
    
    @validator('new_password_confirm')
    def passwords_match(cls, v, values):
        """Verifica se as senhas coincidem"""
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Novas senhas não coincidem')
        return v


class RefreshTokenSchema(BaseModel):
    """Schema para refresh token"""
    refresh_token: str


class Enable2FASchema(BaseModel):
    """Schema para habilitar 2FA"""
    totp_code: str = Field(..., min_length=6, max_length=6)


class Disable2FASchema(BaseModel):
    """Schema para desabilitar 2FA"""
    password: str
    totp_code: Optional[str] = Field(None, min_length=6, max_length=6)


class ResetPasswordRequestSchema(BaseModel):
    """Schema para solicitação de reset de senha"""
    email: EmailStr


class ResetPasswordConfirmSchema(BaseModel):
    """Schema para confirmação de reset de senha"""
    token: str
    new_password: str = Field(..., min_length=12, max_length=128)
    new_password_confirm: str = Field(..., min_length=12, max_length=128)
    
    @validator('new_password')
    def validate_new_password(cls, v):
        """Valida força da nova senha"""
        if len(v) < 12:
            raise ValueError('Nova senha deve ter pelo menos 12 caracteres')
        
        if not re.search(r'[A-Z]', v):
            raise ValueError('Nova senha deve conter pelo menos uma letra maiúscula')
        
        if not re.search(r'[a-z]', v):
            raise ValueError('Nova senha deve conter pelo menos uma letra minúscula')
        
        if not re.search(r'\d', v):
            raise ValueError('Nova senha deve conter pelo menos um número')
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Nova senha deve conter pelo menos um caractere especial')
        
        return v
    
    @validator('new_password_confirm')
    def passwords_match(cls, v, values):
        """Verifica se as senhas coincidem"""
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Novas senhas não coincidem')
        return v


# Schemas de Response

class TokenResponse(BaseModel):
    """Schema de resposta para tokens"""
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int


class UserResponse(BaseModel):
    """Schema de resposta para dados do usuário"""
    id: str
    email: str
    full_name: str
    phone: Optional[str] = None
    avatar: Optional[str] = None
    email_verified: bool
    phone_verified: bool
    two_factor_enabled: bool
    created_at: datetime
    last_login: Optional[datetime] = None


class LoginResponse(BaseModel):
    """Schema de resposta para login"""
    success: bool
    requires_2fa: bool = False
    requires_unlock: bool = False
    temp_token: Optional[str] = None
    tokens: Optional[TokenResponse] = None
    user: Optional[UserResponse] = None
    message: Optional[str] = None
    error: Optional[str] = None
    attempts_remaining: Optional[int] = None


class Setup2FAResponse(BaseModel):
    """Schema de resposta para setup 2FA"""
    secret: str
    qr_code: str
    backup_codes: List[str]
    totp_uri: str


class MessageResponse(BaseModel):
    """Schema de resposta genérica com mensagem"""
    success: bool
    message: str
    error: Optional[str] = None


class ValidationErrorResponse(BaseModel):
    """Schema de resposta para erros de validação"""
    success: bool = False
    error: str
    details: Optional[Dict[str, Any]] = None


class UserSessionResponse(BaseModel):
    """Schema de resposta para sessões do usuário"""
    session_key: str
    ip_address: str
    user_agent: str
    is_active: bool
    last_activity: datetime
    created_at: datetime
    expires_at: datetime


class ProfileUpdateSchema(BaseModel):
    """Schema para atualização de perfil"""
    full_name: Optional[str] = Field(None, min_length=2, max_length=150)
    phone: Optional[str] = Field(None, max_length=20)
    
    @validator('phone')
    def validate_phone(cls, v):
        """Valida formato do telefone"""
        if v and not re.match(r'^\+?1?\d{9,15}$', v):
            raise ValueError('Formato de telefone inválido')
        return v


class LoginAttemptResponse(BaseModel):
    """Schema de resposta para tentativas de login"""
    email: str
    ip_address: str
    status: str
    failure_reason: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    attempted_at: datetime