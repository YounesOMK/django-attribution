import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class DjangoAttributionConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "django_attribution"
    verbose_name = "Django Attribution"
