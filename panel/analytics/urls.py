"""
Analytics app URL'lari.
"""

from django.urls import path
from . import views

# app_name — template da {% url 'analytics:main' %} ko'rinishida ishlatiladi
app_name = 'analytics'

urlpatterns = [
    # /analytics/ — asosiy statistika sahifasi
    path('', views.analytics_main, name='main'),
]
