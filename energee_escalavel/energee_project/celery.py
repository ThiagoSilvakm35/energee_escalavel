"""
Celery configuration for energee_project.
Processamento Assíncrono de Faturas e Relatórios
"""

import os
from celery import Celery
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'energee_project.settings')

app = Celery('energee_project')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Celery Beat Configuration
app.conf.beat_schedule = {
    'processar-faturas-pendentes': {
        'task': 'apps.faturas.tasks.processar_faturas_pendentes',
        'schedule': 300.0,  # Every 5 minutes
    },
    'gerar-relatorios-diarios': {
        'task': 'apps.relatorios.tasks.gerar_relatorios_diarios',
        'schedule': 86400.0,  # Daily
    },
    'limpar-cache-expirado': {
        'task': 'apps.core.tasks.limpar_cache_expirado',
        'schedule': 3600.0,  # Hourly
    },
    'backup-dados-criticos': {
        'task': 'apps.core.tasks.backup_dados_criticos',
        'schedule': 21600.0,  # Every 6 hours
    },
}

app.conf.task_routes = {
    'apps.faturas.tasks.*': {'queue': 'faturas'},
    'apps.relatorios.tasks.*': {'queue': 'relatorios'},
    'apps.core.tasks.*': {'queue': 'system'},
}

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')