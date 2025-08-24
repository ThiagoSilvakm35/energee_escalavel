from django.apps import AppConfig


class AuthenticationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.authentication'
    verbose_name = 'Autenticação e Autorização'
    
    def ready(self):
        # Import signal handlers
        import apps.authentication.signals