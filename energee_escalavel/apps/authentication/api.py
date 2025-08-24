"""
APIs RESTful Assíncronas de Autenticação - Django Ninja
"""
from ninja import Router
from django.http import HttpRequest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone
from apps.authentication.jwt_auth import AuthService, JWTService, jwt_auth
from apps.authentication.schemas import (
    LoginSchema, Login2FASchema, RegisterSchema, ChangePasswordSchema,
    RefreshTokenSchema, Enable2FASchema, Disable2FASchema,
    ResetPasswordRequestSchema, ResetPasswordConfirmSchema,
    ProfileUpdateSchema, LoginResponse, UserResponse, TokenResponse,
    Setup2FAResponse, MessageResponse, ValidationErrorResponse,
    UserSessionResponse, LoginAttemptResponse
)
from apps.authentication.models import UserSession, LoginAttempt
from typing import List
import asyncio
from asgiref.sync import sync_to_async

User = get_user_model()
auth_router = Router()


def get_client_ip(request: HttpRequest) -> str:
    """Obtém IP real do cliente"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def get_user_agent(request: HttpRequest) -> str:
    """Obtém User-Agent do cliente"""
    return request.META.get('HTTP_USER_AGENT', '')


@auth_router.post("/login", response=LoginResponse)
async def login(request: HttpRequest, data: LoginSchema):
    """
    Endpoint de login com suporte a 2FA
    """
    ip_address = get_client_ip(request)
    user_agent = get_user_agent(request)
    
    # Verifica rate limiting por IP
    cache_key = f"login_attempts:{ip_address}"
    attempts = cache.get(cache_key, 0)
    
    if attempts >= 5:
        return LoginResponse(
            success=False,
            error="Muitas tentativas de login. Tente novamente em 15 minutos."
        )
    
    # Autentica usuário
    result = await sync_to_async(AuthService.authenticate_user)(
        email=data.email,
        password=data.password,
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    # Incrementa contador se falhou
    if not result['success']:
        cache.set(cache_key, attempts + 1, 900)  # 15 minutos
    else:
        cache.delete(cache_key)  # Reseta contador em caso de sucesso
    
    return LoginResponse(**result)


@auth_router.post("/login/2fa", response=LoginResponse)
async def login_2fa(request: HttpRequest, data: Login2FASchema):
    """
    Completa login com verificação 2FA
    """
    ip_address = get_client_ip(request)
    user_agent = get_user_agent(request)
    
    result = await sync_to_async(AuthService.verify_2fa_and_complete_login)(
        temp_token=data.temp_token,
        totp_code=data.totp_code,
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    return LoginResponse(**result)


@auth_router.post("/refresh", response=TokenResponse)
async def refresh_token(request: HttpRequest, data: RefreshTokenSchema):
    """
    Renova token de acesso usando refresh token
    """
    result = await sync_to_async(JWTService.refresh_token)(data.refresh_token)
    
    if not result:
        return {"error": "Token inválido ou expirado"}, 401
    
    return TokenResponse(**result)


@auth_router.post("/logout")
async def logout(request: HttpRequest, user: User = jwt_auth):
    """
    Encerra sessão do usuário
    """
    # Revoga todos os tokens do usuário
    await sync_to_async(JWTService.revoke_tokens)(user)
    
    return {"success": True, "message": "Logout realizado com sucesso"}


@auth_router.post("/register", response=UserResponse)
async def register(request: HttpRequest, data: RegisterSchema):
    """
    Registro de novo usuário
    """
    # Verifica se email já existe
    if await sync_to_async(User.objects.filter(email=data.email).exists)():
        return {"error": "Email já cadastrado"}, 400
    
    # Cria usuário
    user = await sync_to_async(User.objects.create_user)(
        username=data.email,
        email=data.email,
        password=data.password,
        full_name=data.full_name,
        phone=data.phone,
        terms_accepted=data.terms_accepted,
        terms_accepted_at=timezone.now()
    )
    
    return UserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.get_full_name(),
        phone=user.phone,
        email_verified=user.email_verified,
        phone_verified=user.phone_verified,
        two_factor_enabled=user.two_factor_enabled,
        created_at=user.created_at,
        last_login=user.last_login
    )


@auth_router.get("/me", response=UserResponse)
async def get_current_user(request: HttpRequest, user: User = jwt_auth):
    """
    Retorna dados do usuário autenticado
    """
    return UserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.get_full_name(),
        phone=user.phone,
        avatar=user.avatar.url if user.avatar else None,
        email_verified=user.email_verified,
        phone_verified=user.phone_verified,
        two_factor_enabled=user.two_factor_enabled,
        created_at=user.created_at,
        last_login=user.last_login
    )


@auth_router.put("/me", response=UserResponse)
async def update_profile(request: HttpRequest, data: ProfileUpdateSchema, user: User = jwt_auth):
    """
    Atualiza perfil do usuário
    """
    if data.full_name:
        user.full_name = data.full_name
    
    if data.phone:
        user.phone = data.phone
        user.phone_verified = False  # Precisa verificar novamente
    
    await sync_to_async(user.save)(update_fields=['full_name', 'phone', 'phone_verified'])
    
    return UserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.get_full_name(),
        phone=user.phone,
        avatar=user.avatar.url if user.avatar else None,
        email_verified=user.email_verified,
        phone_verified=user.phone_verified,
        two_factor_enabled=user.two_factor_enabled,
        created_at=user.created_at,
        last_login=user.last_login
    )


@auth_router.post("/change-password", response=MessageResponse)
async def change_password(request: HttpRequest, data: ChangePasswordSchema, user: User = jwt_auth):
    """
    Altera senha do usuário
    """
    # Verifica senha atual
    if not await sync_to_async(user.check_password)(data.current_password):
        return MessageResponse(success=False, error="Senha atual incorreta")
    
    # Altera senha
    await sync_to_async(user.set_password)(data.new_password)
    await sync_to_async(user.save)(update_fields=['password'])
    
    # Revoga todas as sessões ativas (força novo login)
    await sync_to_async(JWTService.revoke_tokens)(user)
    
    return MessageResponse(success=True, message="Senha alterada com sucesso")


@auth_router.get("/2fa/setup", response=Setup2FAResponse)
async def setup_2fa(request: HttpRequest, user: User = jwt_auth):
    """
    Configura 2FA para o usuário
    """
    result = await sync_to_async(AuthService.setup_2fa)(user)
    return Setup2FAResponse(**result)


@auth_router.post("/2fa/enable", response=MessageResponse)
async def enable_2fa(request: HttpRequest, data: Enable2FASchema, user: User = jwt_auth):
    """
    Habilita 2FA após verificação do código
    """
    result = await sync_to_async(AuthService.enable_2fa)(user, data.totp_code)
    return MessageResponse(**result)


@auth_router.post("/2fa/disable", response=MessageResponse)
async def disable_2fa(request: HttpRequest, data: Disable2FASchema, user: User = jwt_auth):
    """
    Desabilita 2FA
    """
    result = await sync_to_async(AuthService.disable_2fa)(
        user, data.password, data.totp_code
    )
    return MessageResponse(**result)


@auth_router.get("/sessions", response=List[UserSessionResponse])
async def get_user_sessions(request: HttpRequest, user: User = jwt_auth):
    """
    Lista sessões ativas do usuário
    """
    sessions = await sync_to_async(list)(
        UserSession.objects.filter(user=user, is_active=True).order_by('-last_activity')
    )
    
    return [
        UserSessionResponse(
            session_key=session.session_key,
            ip_address=session.ip_address,
            user_agent=session.user_agent,
            is_active=session.is_active,
            last_activity=session.last_activity,
            created_at=session.created_at,
            expires_at=session.expires_at
        )
        for session in sessions
    ]


@auth_router.delete("/sessions/{session_key}")
async def terminate_session(request: HttpRequest, session_key: str, user: User = jwt_auth):
    """
    Termina uma sessão específica
    """
    try:
        session = await sync_to_async(UserSession.objects.get)(
            user=user, session_key=session_key, is_active=True
        )
        await sync_to_async(session.terminate)()
        
        return {"success": True, "message": "Sessão terminada"}
    except UserSession.DoesNotExist:
        return {"error": "Sessão não encontrada"}, 404


@auth_router.delete("/sessions")
async def terminate_all_sessions(request: HttpRequest, user: User = jwt_auth):
    """
    Termina todas as sessões do usuário
    """
    await sync_to_async(JWTService.revoke_tokens)(user)
    return {"success": True, "message": "Todas as sessões foram terminadas"}


@auth_router.get("/login-attempts", response=List[LoginAttemptResponse])
async def get_login_attempts(request: HttpRequest, user: User = jwt_auth):
    """
    Lista tentativas de login recentes do usuário
    """
    attempts = await sync_to_async(list)(
        LoginAttempt.objects.filter(user=user).order_by('-attempted_at')[:20]
    )
    
    return [
        LoginAttemptResponse(
            email=attempt.email,
            ip_address=attempt.ip_address,
            status=attempt.status,
            failure_reason=attempt.failure_reason,
            country=attempt.country,
            city=attempt.city,
            attempted_at=attempt.attempted_at
        )
        for attempt in attempts
    ]


@auth_router.post("/password-reset/request", response=MessageResponse)
async def request_password_reset(request: HttpRequest, data: ResetPasswordRequestSchema):
    """
    Solicita reset de senha
    """
    try:
        user = await sync_to_async(User.objects.get)(email=data.email)
        
        # Aqui seria implementado o envio de email com token
        # Por enquanto, apenas simula o processo
        
        return MessageResponse(
            success=True,
            message="Se este email estiver cadastrado, você receberá instruções para redefinir sua senha"
        )
    except User.DoesNotExist:
        # Não revela se o email existe ou não por segurança
        return MessageResponse(
            success=True,
            message="Se este email estiver cadastrado, você receberá instruções para redefinir sua senha"
        )


@auth_router.post("/password-reset/confirm", response=MessageResponse)
async def confirm_password_reset(request: HttpRequest, data: ResetPasswordConfirmSchema):
    """
    Confirma reset de senha com token
    """
    # Aqui seria implementada a verificação do token e reset da senha
    # Por enquanto, apenas simula o processo
    
    return MessageResponse(
        success=True,
        message="Senha redefinida com sucesso"
    )