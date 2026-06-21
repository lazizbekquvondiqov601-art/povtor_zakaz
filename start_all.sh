#!/usr/bin/env bash
# Bot + Web bitta containerda. Bot background, gunicorn foreground.
set -e

cd "$(dirname "$0")"

echo ">>> migrate..."
python panel/manage.py migrate --noinput

echo ">>> superuser tekshirilmoqda..."
python - <<'PYEOF'
import os, django, sys
sys.path.insert(0, 'panel')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'panel_config.settings')
django.setup()
from django.contrib.auth import get_user_model
User = get_user_model()
username = os.environ.get('PANEL_ADMIN_USERNAME', 'admin')
password = os.environ.get('PANEL_ADMIN_PASSWORD', '')
email    = os.environ.get('PANEL_ADMIN_EMAIL', 'admin@example.com')
if password and not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username=username, email=email, password=password)
    print(f">>> Superuser '{username}' yaratildi.")
else:
    print(f">>> Superuser '{username}' allaqachon mavjud.")
PYEOF

echo ">>> collectstatic..."
python panel/manage.py collectstatic --noinput --clear 2>/dev/null || true

echo ">>> Bot background da ishga tushyapti..."
python bot.py &
BOT_PID=$!
echo ">>> Bot PID: $BOT_PID"

echo ">>> Gunicorn PORT=${PORT:-8000} da ishga tushyapti..."
exec gunicorn panel.panel_config.wsgi:application \
    --chdir panel \
    --bind "0.0.0.0:${PORT:-8000}" \
    --workers 2 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
