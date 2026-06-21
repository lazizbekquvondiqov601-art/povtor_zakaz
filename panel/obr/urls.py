"""
OBR ilovasining URL marshrutlari.

/obr/                          -> obr_root   (barcha kategoriyalar)
/obr/<category>/               -> obr_sub    (podkategoriyalar)
/obr/<category>/<subcategory>/ -> obr_stat   (statistika)
"""

from django.urls import path
from . import views

app_name = 'obr'

urlpatterns = [
    # Bosh sahifa — kategoriyalar ro'yxati
    path('', views.obr_root, name='root'),

    # Tanlangan qatorlarni Telegram kanalga yuborish (POST, JSON)
    # MUHIM: 'stat' dan OLDIN yozilishi shart — 'path:' greedy match qiladi,
    # aks holda "<subcategory>/send/" stat ichiga yutilib ketadi.
    path('<str:category>/<path:subcategory>/send/', views.obr_send_telegram, name='send_telegram'),

    # Statistika — kategoriya + podkategoriya
    # path: converter — '/' belgisini ham qabul qiladi (masalan: "Рубашка с кр/р")
    path('<str:category>/<path:subcategory>/', views.obr_stat, name='stat'),

    # Podkategoriyalar — kategoriya nomi URL'da o'zgaruvchi
    # (stat'dan keyin yoziladi, chunki path: greedy match qiladi)
    path('<str:category>/', views.obr_sub, name='sub'),
]
