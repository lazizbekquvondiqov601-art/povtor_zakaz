#!/usr/bin/env bash
# Bot + Web bitta containerda. Bot background, gunicorn foreground.
set -e

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$APP_DIR"

echo ">>> migrate..."
cd "$APP_DIR/panel"
python manage.py migrate --noinput

echo ">>> superuser..."
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
    print(f">>> Superuser '{username}' yaratildi.")
PYEOF

echo ">>> collectstatic..."
python manage.py collectstatic --noinput --clear 2>/dev/null || true

echo ">>> Bot background..."
cd "$APP_DIR"
python bot.py &
echo ">>> Bot PID: $!"

echo ">>> Gunicorn PORT=${PORT:-8000}..."
cd "$APP_DIR/panel"
exec gunicorn panel_config.wsgi:application \
    --bind "0.0.0.0:${PORT:-8000}" \
    --workers 2 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
