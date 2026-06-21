#!/usr/bin/env bash
# Railway "web" service ishga tushirish skripti.
# Maqsad: gunicorn ALBATTA $PORT ga bog'lanishi (502 ni oldini olish).
set -e

cd "$(dirname "$0")/panel"

echo ">>> [web] migrate boshlandi..."
python manage.py migrate --noinput

echo ">>> [web] superuser tekshirilmoqda..."
python - <<'PYEOF'
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'panel_config.settings')
django.setup()
from django.contrib.auth import get_user_model
User = get_user_model()
username = os.environ.get('PANEL_ADMIN_USERNAME', 'admin')
password = os.environ.get('PANEL_ADMIN_PASSWORD', '')
email    = os.environ.get('PANEL_ADMIN_EMAIL', 'admin@example.com')
if password and not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username=username, email=email, password=password)
    print(f">>> [web] Superuser '{username}' yaratildi.")
else:
    print(f">>> [web] Superuser '{username}' allaqachon mavjud yoki PANEL_ADMIN_PASSWORD berilmagan.")
PYEOF

echo ">>> [web] collectstatic boshlandi (xato bo'lsa ham davom etadi)..."
python manage.py collectstatic --noinput --clear || echo ">>> [web] collectstatic o'tmadi, davom etamiz"

echo ">>> [web] gunicorn ishga tushyapti, PORT=${PORT:-8000}"
exec gunicorn panel_config.wsgi:application \
    --bind "0.0.0.0:${PORT:-8000}" \
    --workers 2 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
