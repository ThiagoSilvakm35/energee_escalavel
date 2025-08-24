"""
Sistema de Autenticação JWT com 2FA
"""
import jwt
import pyotp
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from django.conf import settings
from django.contrib.auth import authenticate
from django.core.cache import cache
from django.utils import timezone
from ninja.security import HttpBearer
from ninja import Header
from apps.authentication.models import User, LoginAttempt, UserSession
from apps.core.middleware import get_current_tenant


class JWTAuth(HttpBearer):
    """
    Autenticação JWT para Django Ninja
    """
    
    def authenticate(self, request, token: str) -> Optional[User]:
        """
        Autentica usuário através do token JWT
        """
        try:
            # Decodifica o token
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )
            
            # Verifica se é token de acesso
            if payload.get('type') != 'access':
                return None
                
            # Busca o usuário
            user_id = payload.get('user_id')
            user = User.objects.get(id=user_id)
            
            # Verifica se a conta não está bloqueada
            if user.is_locked:
                return None
            
            # Verifica se a sessão está ativa
            session_key = payload.get('session_key')
            if session_key:
                session = UserSession.objects.filter(
                    user=user,
                    session_key=session_key,
                    is_active=True
                ).first()
                
                if not session or session.is_expired:
                    return None
            
            # Atualiza última atividade
            cache.set(f"user_activity:{user.id}", timezone.now(), 300)
            
            return user
            
        except (jwt.ExpiredSignatureError, jwt.DecodeError, User.DoesNotExist):
            return None


class JWTService:
    """
    Serviço para gerenciamento de tokens JWT
    """
    
    @staticmethod
    def generate_tokens(user: User, session_key: str = None) -> Dict[str, Any]:
        """
        Gera tokens de acesso e refresh para o usuário
        """
        now = datetime.utcnow()
        
        # Payload base
        base_payload = {
            'user_id': str(user.id),
            'email': user.email,
            'iat': now,
        }
        
        if session_key:
            base_payload['session_key'] = session_key
        
        # Token de acesso
        access_payload = {
            **base_payload,
            'type': 'access',
            'exp': now + timedelta(seconds=settings.JWT_ACCESS_TOKEN_LIFETIME),
        }
        
        # Token de refresh
        refresh_payload = {
            **base_payload,
            'type': 'refresh',
            'exp': now + timedelta(seconds=settings.JWT_REFRESH_TOKEN_LIFETIME),
        }
        
        access_token = jwt.encode(
            access_payload,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )
        
        refresh_token = jwt.encode(
            refresh_payload,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )
        
        return {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'token_type': 'Bearer',
            'expires_in': settings.JWT_ACCESS_TOKEN_LIFETIME,
        }
    
    @staticmethod
    def refresh_token(refresh_token: str) -> Optional[Dict[str, Any]]:
        """
        Renova token de acesso usando refresh token
        """
        try:
            payload = jwt.decode(
                refresh_token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )
            
            if payload.get('type') != 'refresh':
                return None
            
            user = User.objects.get(id=payload.get('user_id'))
            
            if user.is_locked:
                return None
            
            return JWTService.generate_tokens(
                user,
                payload.get('session_key')
            )
            
        except (jwt.ExpiredSignatureError, jwt.DecodeError, User.DoesNotExist):
            return None
    
    @staticmethod
    def revoke_tokens(user: User):
        """
        Revoga todos os tokens do usuário
        """
        # Termina todas as sessões ativas
        UserSession.objects.filter(user=user, is_active=True).update(
            is_active=False
        )
        
        # Adiciona tokens à blacklist (seria implementado com Redis)
        cache.set(f"revoked_tokens:{user.id}", True, 86400)


class AuthService:
    """
    Serviço de autenticação com 2FA
    """
    
    @staticmethod
    def authenticate_user(email: str, password: str, ip_address: str, user_agent: str) -> Dict[str, Any]:
        """
        Autentica usuário com email e senha
        """
        # Registra tentativa de login
        def log_attempt(status: str, failure_reason: str = ''):
            LoginAttempt.objects.create(
                user=user if 'user' in locals() else None,
                email=email,
                ip_address=ip_address,
                user_agent=user_agent,
                status=status,
                failure_reason=failure_reason
            )
        
        try:
            user = User.objects.get(email=email)
            
            # Verifica se a conta está bloqueada
            if user.is_locked:
                log_attempt('blocked', 'Conta bloqueada')
                return {
                    'success': False,
                    'error': 'Conta temporariamente bloqueada',
                    'requires_unlock': True
                }
            
            # Autentica usuário
            authenticated_user = authenticate(username=email, password=password)
            
            if not authenticated_user:
                user.increment_failed_login()
                log_attempt('failed', 'Credenciais inválidas')
                return {
                    'success': False,
                    'error': 'Credenciais inválidas',
                    'attempts_remaining': 5 - user.failed_login_attempts
                }
            
            # Reseta tentativas falhadas
            user.reset_failed_login()
            user.last_login_ip = ip_address
            user.save(update_fields=['last_login_ip'])
            
            # Verifica se 2FA está habilitado
            if user.two_factor_enabled:
                # Gera token temporário para 2FA
                temp_token = JWTService.generate_temp_2fa_token(user)
                log_attempt('success', '2FA pendente')
                
                return {
                    'success': True,
                    'requires_2fa': True,
                    'temp_token': temp_token,
                    'message': 'Digite o código do seu aplicativo autenticador'
                }
            
            # Login sem 2FA
            session = AuthService.create_user_session(user, ip_address, user_agent)
            tokens = JWTService.generate_tokens(user, session.session_key)
            
            log_attempt('success')
            
            return {
                'success': True,
                'requires_2fa': False,
                'tokens': tokens,
                'user': {
                    'id': str(user.id),
                    'email': user.email,
                    'full_name': user.get_full_name(),
                }
            }
            
        except User.DoesNotExist:
            log_attempt('failed', 'Usuário não encontrado')
            return {
                'success': False,
                'error': 'Credenciais inválidas'
            }
    
    @staticmethod
    def verify_2fa_and_complete_login(temp_token: str, totp_code: str, ip_address: str, user_agent: str) -> Dict[str, Any]:
        """
        Verifica código 2FA e completa o login
        """
        try:
            # Decodifica token temporário
            payload = jwt.decode(
                temp_token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )
            
            if payload.get('type') != 'temp_2fa':
                return {'success': False, 'error': 'Token inválido'}
            
            user = User.objects.get(id=payload.get('user_id'))
            
            # Verifica código TOTP
            if user.verify_totp(totp_code):
                # Cria sessão e tokens
                session = AuthService.create_user_session(user, ip_address, user_agent)
                tokens = JWTService.generate_tokens(user, session.session_key)
                
                return {
                    'success': True,
                    'tokens': tokens,
                    'user': {
                        'id': str(user.id),
                        'email': user.email,
                        'full_name': user.get_full_name(),
                    }
                }
            else:
                # Verifica se é código de backup
                if user.use_backup_code(totp_code):
                    session = AuthService.create_user_session(user, ip_address, user_agent)
                    tokens = JWTService.generate_tokens(user, session.session_key)
                    
                    return {
                        'success': True,
                        'tokens': tokens,
                        'backup_code_used': True,
                        'user': {
                            'id': str(user.id),
                            'email': user.email,
                            'full_name': user.get_full_name(),
                        }
                    }
                
                return {'success': False, 'error': 'Código 2FA inválido'}
                
        except (jwt.ExpiredSignatureError, jwt.DecodeError, User.DoesNotExist):
            return {'success': False, 'error': 'Token expirado ou inválido'}
    
    @staticmethod
    def create_user_session(user: User, ip_address: str, user_agent: str) -> UserSession:
        """
        Cria nova sessão para o usuário
        """
        import secrets
        
        session_key = secrets.token_hex(20)
        expires_at = timezone.now() + timedelta(hours=8)  # 8 horas
        
        session = UserSession.objects.create(
            user=user,
            session_key=session_key,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=expires_at
        )
        
        return session
    
    @staticmethod
    def setup_2fa(user: User) -> Dict[str, Any]:
        """
        Configura 2FA para o usuário
        """
        # Gera segredo TOTP
        secret = user.generate_totp_secret()
        
        # Gera QR Code
        qr_code = user.get_qr_code()
        
        # Gera códigos de backup
        backup_codes = user.generate_backup_codes()
        
        return {
            'secret': secret,
            'qr_code': qr_code,
            'backup_codes': backup_codes,
            'totp_uri': user.get_totp_uri()
        }
    
    @staticmethod
    def enable_2fa(user: User, totp_code: str) -> Dict[str, Any]:
        """
        Habilita 2FA após verificação do código
        """
        if user.verify_totp(totp_code):
            user.two_factor_enabled = True
            user.save(update_fields=['two_factor_enabled'])
            
            return {
                'success': True,
                'message': '2FA habilitado com sucesso'
            }
        
        return {
            'success': False,
            'error': 'Código TOTP inválido'
        }
    
    @staticmethod
    def disable_2fa(user: User, password: str, totp_code: str = None) -> Dict[str, Any]:
        """
        Desabilita 2FA após verificação
        """
        # Verifica senha
        if not user.check_password(password):
            return {'success': False, 'error': 'Senha incorreta'}
        
        # Se 2FA está habilitado, precisa verificar código
        if user.two_factor_enabled and totp_code:
            if not user.verify_totp(totp_code):
                return {'success': False, 'error': 'Código 2FA inválido'}
        
        # Desabilita 2FA
        user.two_factor_enabled = False
        user.totp_secret = ''
        user.backup_codes = []
        user.save(update_fields=['two_factor_enabled', 'totp_secret', 'backup_codes'])
        
        return {
            'success': True,
            'message': '2FA desabilitado com sucesso'
        }


# Instância da autenticação JWT
jwt_auth = JWTAuth()