"""
Django sozlamalari — Super Admin Panel uchun.

Ikki baza ishlatiladi:
  - default  -> panel_data.db (panel foydalanuvchilari, auth)
  - botdb    -> Data_Model.db (bot ma'lumotlari, faqat o'qish)
"""

import os
import sys
from pathlib import Path

# BASE_DIR — panel/ papkasini ko'rsatadi (manage.py joylashgan joy)
BASE_DIR = Path(__file__).resolve().parent.parent

# Bot funksiyalarini import qila olish uchun loyiha ildizini sys.path ga qo'shamiz
# BASE_DIR.parent = povtor-zakaz-bot-button/
sys.path.insert(0, str(BASE_DIR.parent))

# db_manager SQLAlchemy uchun absolute DB yo'li
# config.py "sqlite:///Data_Model.db" (nisbiy) ishlatadi — panel/ dan noto'g'ri ochiladi
# DATABASE_URL env var orqali to'g'ri absolute yo'lni beramiz
_db_abs = str(BASE_DIR.parent / 'Data_Model.db').replace('\\', '/')
os.environ.setdefault('DATABASE_URL', f'sqlite:///{_db_abs}')

# --- Asosiy sozlamalar ---
SECRET_KEY = 'django-insecure-panel-super-admin-change-me-in-production'
DEBUG = True
ALLOWED_HOSTS = ['*']  # development uchun

# --- O'rnatilgan ilovalar ---
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Mahalliy ilovalar
    'core',
    'botdb',
    'obr',   # Asosiy Zakaz moduli

    # Yangi modullar
    'supplier',
    'analytics',
    'stock',
    'panel_settings',
]

# --- Middleware lar ---
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',

    # Bizning middleware — faqat login qilganlar kira oladi
    'core.middleware.SuperAdminOnlyMiddleware',
]

ROOT_URLCONF = 'panel_config.urls'

# --- Shablonlar ---
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,  # ilovalar ichidagi templates papkasidan ham qidiradi
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'panel_config.wsgi.application'

# --- Ma'lumotlar bazalari (ikkita) ---
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR.parent / 'panel_data.db',
    },
    'botdb': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR.parent / 'Data_Model.db',
        'OPTIONS': {'timeout': 20},
    },
}

# Router — qaysi modelni qaysi bazaga yuborishni hal qiladi
DATABASE_ROUTERS = ['panel_config.db_router.BotDbRouter']

# --- Foydalanuvchi modeli ---
AUTH_USER_MODEL = 'core.PanelUser'

# Login sahifasi manzili
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/login/'

# --- Parol tekshiruvi ---
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# --- Til va vaqt ---
LANGUAGE_CODE = 'uz'
TIME_ZONE = 'Asia/Tashkent'
USE_I18N = True
USE_TZ = True

# --- Statik fayllar ---
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Default primary key
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
