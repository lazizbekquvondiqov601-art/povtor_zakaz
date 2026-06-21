web: cd panel && python manage.py migrate --noinput && python manage.py collectstatic --noinput && gunicorn panel_config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 2
worker: python bot.py
