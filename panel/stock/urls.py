"""
Stock app URL'lari.
"""

from django.urls import path
from . import views

# app_name — template da {% url 'stock:main' %} ko'rinishida ishlatiladi
app_name = 'stock'

urlpatterns = [
    # /stock/ — qoldiqlar asosiy sahifasi
    path('', views.stock_main, name='main'),
]
