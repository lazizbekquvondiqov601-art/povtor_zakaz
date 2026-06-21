"""core ilovasining sozlamalari."""

from django.apps import AppConfig


class CoreConfig(AppConfig):
    """Asosiy panel ilovasi."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    verbose_name = 'Asosiy panel'
