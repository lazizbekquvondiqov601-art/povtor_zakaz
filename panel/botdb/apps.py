"""botdb ilovasining sozlamalari."""

from django.apps import AppConfig


class BotdbConfig(AppConfig):
    """Bot bazasidagi jadvallar uchun Django ilovasi."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'botdb'
    verbose_name = 'Bot bazasi (Data_Model.db)'
