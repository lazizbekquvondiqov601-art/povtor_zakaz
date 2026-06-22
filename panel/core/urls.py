"""
core ilovasining URL marshrutlari.
"""

from django.urls import path

from . import views

app_name = 'core'

urlpatterns = [
    # Bosh sahifa — dashboard
    path('', views.dashboard, name='dashboard'),
    path('olik/', views.olik_tovarlar, name='olik'),
    # Telegram WebApp kirish nuqtasi
    path('webapp/', views.webapp_entry, name='webapp'),
    # Billz manual sync
    path('sync/trigger/', views.trigger_sync, name='sync_trigger'),
    path('sync/status/',  views.sync_status,  name='sync_status'),
]
