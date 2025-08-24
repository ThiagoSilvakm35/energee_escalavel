"""
Middleware Multi-Tenant para isolamento de dados por Distribuidora
"""
import threading
from django.http import Http404, HttpResponseForbidden
from django.core.cache import cache
from django.utils.deprecation import MiddlewareMixin
from django.shortcuts import get_object_or_404
from apps.distribuidoras.models import Distribuidora

# Thread-local storage para o tenant atual
_tenant_context = threading.local()


class TenantMiddleware(MiddlewareMixin):
    """
    Middleware que identifica e configura o tenant (Distribuidora) atual
    baseado no subdomínio ou header HTTP
    """
    
    def process_request(self, request):
        """
        Identifica o tenant e configura o contexto
        """
        tenant = self._get_tenant(request)
        
        if tenant:
            # Configura o tenant no contexto thread-local
            set_current_tenant(tenant)
            request.tenant = tenant
            
            # Adiciona informações do tenant ao request
            request.tenant_id = tenant.id
            request.tenant_name = tenant.nome
            
        else:
            # Para APIs públicas ou admin, permite sem tenant
            if self._is_public_path(request.path):
                set_current_tenant(None)
                request.tenant = None
            else:
                # Endpoint privado sem tenant válido
                return HttpResponseForbidden("Tenant não identificado")
    
    def process_response(self, request, response):
        """
        Limpa o contexto do tenant após a requisição
        """
        clear_current_tenant()
        return response
    
    def _get_tenant(self, request):
        """
        Identifica o tenant através de diferentes métodos
        """
        tenant = None
        
        # Método 1: Header HTTP X-Tenant-ID
        tenant_id = request.META.get('HTTP_X_TENANT_ID')
        if tenant_id:
            tenant = self._get_tenant_by_id(tenant_id)
        
        # Método 2: Subdomínio
        if not tenant:
            subdomain = self._extract_subdomain(request)
            if subdomain:
                tenant = self._get_tenant_by_subdomain(subdomain)
        
        # Método 3: URL parameter (?tenant=xxx)
        if not tenant:
            tenant_param = request.GET.get('tenant')
            if tenant_param:
                tenant = self._get_tenant_by_id(tenant_param)
        
        return tenant
    
    def _get_tenant_by_id(self, tenant_id):
        """
        Busca tenant por ID com cache
        """
        cache_key = f"tenant:{tenant_id}"
        tenant = cache.get(cache_key)
        
        if not tenant:
            try:
                tenant = Distribuidora.objects.get(id=tenant_id, status='ativo')
                cache.set(cache_key, tenant, 300)  # Cache por 5 minutos
            except Distribuidora.DoesNotExist:
                return None
        
        return tenant
    
    def _get_tenant_by_subdomain(self, subdomain):
        """
        Busca tenant por subdomínio com cache
        """
        cache_key = f"tenant:subdomain:{subdomain}"
        tenant = cache.get(cache_key)
        
        if not tenant:
            try:
                tenant = Distribuidora.objects.get(slug=subdomain, status='ativo')
                cache.set(cache_key, tenant, 300)  # Cache por 5 minutos
            except Distribuidora.DoesNotExist:
                return None
        
        return tenant
    
    def _extract_subdomain(self, request):
        """
        Extrai subdomínio do host HTTP
        """
        host = request.get_host().split(':')[0]  # Remove porta se houver
        parts = host.split('.')
        
        # Se tem mais de 2 partes, o primeiro é o subdomínio
        if len(parts) > 2:
            return parts[0]
        
        return None
    
    def _is_public_path(self, path):
        """
        Verifica se é um endpoint público que não precisa de tenant
        """
        public_paths = [
            '/admin/',
            '/api/docs/',
            '/api/openapi.json',
            '/health/',
            '/api/auth/login/',
            '/api/auth/register/',
            '/__debug__/',
        ]
        
        return any(path.startswith(public_path) for public_path in public_paths)


class TenantQuerySetMixin:
    """
    Mixin para QuerySets que filtra automaticamente pelo tenant atual
    """
    
    def for_tenant(self, tenant=None):
        """
        Filtra QuerySet pelo tenant especificado ou atual
        """
        if tenant is None:
            tenant = get_current_tenant()
        
        if tenant:
            return self.filter(distribuidora=tenant)
        
        return self.none()


class TenantManager(models.Manager):
    """
    Manager que filtra automaticamente pelo tenant atual
    """
    
    def get_queryset(self):
        """
        Retorna QuerySet filtrado pelo tenant atual
        """
        queryset = super().get_queryset()
        tenant = get_current_tenant()
        
        if tenant and hasattr(self.model, 'distribuidora'):
            queryset = queryset.filter(distribuidora=tenant)
        
        return queryset
    
    def all_tenants(self):
        """
        Retorna QuerySet sem filtro de tenant (usar com cuidado)
        """
        return super().get_queryset()


# Funções utilitárias para gerenciar contexto do tenant

def set_current_tenant(tenant):
    """
    Define o tenant atual no contexto thread-local
    """
    _tenant_context.tenant = tenant


def get_current_tenant():
    """
    Retorna o tenant atual do contexto thread-local
    """
    return getattr(_tenant_context, 'tenant', None)


def clear_current_tenant():
    """
    Limpa o tenant do contexto thread-local
    """
    if hasattr(_tenant_context, 'tenant'):
        delattr(_tenant_context, 'tenant')


def require_tenant(view_func):
    """
    Decorator que garante que uma view tem tenant definido
    """
    def wrapper(request, *args, **kwargs):
        if not hasattr(request, 'tenant') or request.tenant is None:
            raise Http404("Tenant não encontrado")
        return view_func(request, *args, **kwargs)
    
    return wrapper


class TenantAwareModel:
    """
    Mixin para models que devem ser tenant-aware
    """
    
    def save(self, *args, **kwargs):
        """
        Override save para definir tenant automaticamente
        """
        if hasattr(self, 'distribuidora') and not self.distribuidora_id:
            tenant = get_current_tenant()
            if tenant:
                self.distribuidora = tenant
        
        super().save(*args, **kwargs)
    
    @classmethod
    def get_for_tenant(cls, tenant=None):
        """
        Retorna QuerySet filtrado pelo tenant
        """
        if tenant is None:
            tenant = get_current_tenant()
        
        if tenant:
            return cls.objects.filter(distribuidora=tenant)
        
        return cls.objects.none()