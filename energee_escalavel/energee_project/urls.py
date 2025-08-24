"""energee_project URL Configuration

Sistema Multi-Tenant para Gestão de Faturas de Energia
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from ninja import NinjaAPI
from apps.authentication.api import auth_router
from apps.distribuidoras.api import distribuidoras_router
from apps.organizacoes.api import organizacoes_router
from apps.usinas.api import usinas_router
from apps.faturas.api import faturas_router
from apps.relatorios.api import relatorios_router

# Django Ninja API Configuration
api = NinjaAPI(
    title="Energee API",
    version="1.0.0",
    description="Sistema Multi-Tenant para Gestão de Faturas de Energia Elétrica",
    docs_url="/api/docs/",
    openapi_url="/api/openapi.json",
)

# Register API Routers
api.add_router("/auth", auth_router, tags=["Autenticação"])
api.add_router("/distribuidoras", distribuidoras_router, tags=["Distribuidoras"])
api.add_router("/organizacoes", organizacoes_router, tags=["Organizações"])
api.add_router("/usinas", usinas_router, tags=["Usinas"])
api.add_router("/faturas", faturas_router, tags=["Faturas"])
api.add_router("/relatorios", relatorios_router, tags=["Relatórios"])

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', api.urls),
    path('health/', include('apps.core.urls')),
]

# Debug Toolbar URLs
if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns

# Static and Media files
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Admin customization
admin.site.site_header = "Energee Admin"
admin.site.site_title = "Energee Admin Portal"
admin.site.index_title = "Bem-vindo ao Energee Admin"