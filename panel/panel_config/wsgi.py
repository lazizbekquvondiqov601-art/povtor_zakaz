"""
WSGI konfiguratsiyasi — production deploy uchun kerak bo'ladi.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'panel_config.settings')

application = get_wsgi_application()
