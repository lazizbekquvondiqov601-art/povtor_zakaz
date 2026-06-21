"""
Supplier app URL'lari.
"""

from django.urls import path
from . import views

# app_name — template da {% url 'supplier:list' %} ko'rinishida ishlatiladi
app_name = 'supplier'

urlpatterns = [
    # /supplier/ — barcha supplierlar ro'yxati
    path('', views.supplier_list, name='list'),

    # /supplier/SUPPLIER_NAME/ — tanlangan supplier tahlili
    path('<str:supplier_name>/', views.supplier_detail, name='detail'),
]
