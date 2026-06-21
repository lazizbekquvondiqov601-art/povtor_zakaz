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
]
