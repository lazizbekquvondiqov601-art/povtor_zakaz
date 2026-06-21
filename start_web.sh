#!/usr/bin/env bash
# Railway "web" service ishga tushirish skripti.
# Maqsad: gunicorn ALBATTA $PORT ga bog'lanishi (502 ni oldini olish).
set -e

cd "$(dirname "$0")/panel"

echo ">>> [web] migrate boshlandi..."
python manage.py migrate --noinput

echo ">>> [web] collectstatic boshlandi (xato bo'lsa ham davom etadi)..."
python manage.py collectstatic --noinput --clear || echo ">>> [web] collectstatic o'tmadi, davom etamiz"

echo ">>> [web] gunicorn ishga tushyapti, PORT=${PORT:-8000}"
exec gunicorn panel_config.wsgi:application \
    --bind "0.0.0.0:${PORT:-8000}" \
    --workers 2 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
