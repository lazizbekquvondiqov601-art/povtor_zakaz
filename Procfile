web: cd panel && python manage.py migrate --noinput && python manage.py collectstatic --noinput && gunicorn panel_config.wsgi --bind 0.0.0.0:$PORT
worker: python bot.py
