from django.urls import path
from . import views

urlpatterns = [
    path('', views.import_tahlil_main, name='import_tahlil'),
]
