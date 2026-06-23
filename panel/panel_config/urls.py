"""
Loyiha bo'yicha asosiy URL'lar.
"""

from django.contrib import admin
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import include, path

urlpatterns = [
    # Django built-in admin (zaxira sifatida)
    path('admin/', admin.site.urls),

    # Login — Django'ning standart LoginView'i, lekin o'zimizning template
    path(
        'login/',
        LoginView.as_view(template_name='core/login.html'),
        name='login',
    ),

    # Logout — chiqishdan keyin login sahifasiga qaytadi (LOGOUT_REDIRECT_URL)
    path('logout/', LogoutView.as_view(), name='logout'),

    # Asosiy ilova — dashboard va qolgan sahifalar
    path('', include('core.urls')),

    # OBR — Asosiy Zakaz moduli
    path('obr/', include('obr.urls')),

    # Yangi modullar
    path('supplier/', include('supplier.urls')),
    path('analytics/', include('analytics.urls')),
    path('stock/', include('stock.urls')),
    path('settings/', include('panel_settings.urls')),
    path('import/', include('import_tahlil.urls')),
]
