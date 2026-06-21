"""
Panel uchun foydalanuvchi modeli.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models


class PanelUser(AbstractUser):
    """
    Super Admin Panel foydalanuvchisi.

    Hozircha AbstractUser dan farqi yo'q, lekin keyinchalik
    rol (role) maydoni qo'shilishi mumkin.
    """

    # Kelajakda role qo'shilishi mumkin. Hozircha is_superuser kifoya.
    # role = models.CharField(max_length=50, default='super_admin')

    class Meta:
        db_table = 'panel_users'
        verbose_name = 'Panel foydalanuvchisi'
        verbose_name_plural = 'Panel foydalanuvchilari'

    def __str__(self):
        return self.username
