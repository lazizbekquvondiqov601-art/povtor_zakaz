import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'panel_config.settings')
django.setup()

from django.test import Client

c = Client()
resp = c.post('/login/', {'username': 'admin', 'password': 'admin1234'})
print('Login:', resp.status_code, resp.get('Location', ''))

pages = [('/', 'Dashboard'), ('/obr/', 'OBR'), ('/supplier/', 'Supplier'),
         ('/analytics/', 'Analytics'), ('/stock/', 'Stock'), ('/settings/', 'Settings')]

for url, name in pages:
    try:
        resp = c.get(url)
        print(f'{name} ({url}): {resp.status_code}')
        if resp.status_code == 500:
            if hasattr(resp, 'context') and resp.context:
                print('  ERROR:', resp.context.get('exception', 'no exception info'))
    except Exception as e:
        print(f'{name} ({url}): EXCEPTION - {e}')
