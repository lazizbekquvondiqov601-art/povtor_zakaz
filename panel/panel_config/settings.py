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
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-panel-super-admin-change-me-in-production')
DEBUG = os.getenv('DEBUG', 'True') == 'True'
ALLOWED_HOSTS = ['*']

# Railway domain uchun CSRF
_web_url = os.getenv('WEB_URL', '')
CSRF_TRUSTED_ORIGINS = [_web_url] if _web_url else []

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
# Railway da DATABASE_URL (Postgres) beriladi -> ikkala connection ham
# bitta umumiy Postgres ga ulanadi. Bu MUHIM: web (Django) va worker (bot)
# alohida servicelarda ishlaydi va faqat umumiy Postgres orqali bir xil
# ma'lumotni ko'radi. Railway file system ephemeral bo'lgani uchun SQLite
# bu yerda ishlamaydi.
#
# Lokal kompyuterda DATABASE_URL Postgres bo'lmasa, eski SQLite fayllarga
# qaytadi (lokal development buzilmaydi).
_pg_url = os.getenv('DATABASE_URL', '')
_is_postgres = _pg_url.startswith('postgres')

if _is_postgres:
    # dj_database_url faqat Postgres rejimida kerak (lokal SQLite da emas)
    import dj_database_url
    # Railway: ikkala connection ham umumiy Postgres ga
    DATABASES = {
        'default': dj_database_url.parse(_pg_url, conn_max_age=600),
        'botdb': dj_database_url.parse(_pg_url, conn_max_age=600),
    }
else:
    # Lokal development: eski SQLite fayllar
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
# static papka bo'lmasa collectstatic xato bermasligi uchun shartli
STATICFILES_DIRS = [BASE_DIR / 'static'] if (BASE_DIR / 'static').exists() else []
STATIC_ROOT = BASE_DIR / 'staticfiles'
# ManifestStaticFilesStorage hamma faylni manifestda topa olmasa har bir
# sahifani 500 qiladi. Production da xavfsizroq Compressed (manifestsiz) variant.
STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'

# Default primary key
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
