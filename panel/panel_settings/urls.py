"""
Panel Settings app URL'lari.
"""

from django.urls import path
from . import views

# app_name — template da {% url 'panel_settings:main' %} ko'rinishida ishlatiladi
app_name = 'panel_settings'

urlpatterns = [
    # /settings/ — sozlamalar ko'rish sahifasi
    path('', views.settings_main, name='main'),

    # /settings/update/ — sozlamalar saqlash (faqat POST)
    path('update/', views.settings_update, name='update'),
]
