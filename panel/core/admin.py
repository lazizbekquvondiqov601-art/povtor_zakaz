"""
Django admin sozlamalari.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import PanelUser

# Panel foydalanuvchilarini Django admin'da boshqarish uchun
admin.site.register(PanelUser, UserAdmin)
