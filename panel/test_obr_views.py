import sys, os
sys.path.insert(0, '..')
os.environ['DJANGO_SETTINGS_MODULE'] = 'panel_config.settings'
import django; django.setup()

from django.test import RequestFactory
from django.contrib.auth import get_user_model
User = get_user_model()
u = User.objects.first()

from obr.views import obr_root, obr_sub, obr_stat
rf = RequestFactory()

# 1. Root page
print("\n=== Test 1: obr_root ===")
req = rf.get('/obr/')
req.user = u; req.session = {}
try:
    r = obr_root(req)
    print(f"Status: {r.status_code}")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback; traceback.print_exc()

# 2. Sub page
print("\n=== Test 2: obr_sub ===")
req2 = rf.get('/obr/test/', {'macro_sub': 'Боди', 'linked': '1', 'macro_cat': 'Новорождённый'})
req2.user = u; req2.session = {}
try:
    r2 = obr_sub(req2, category='Новорождённый')
    print(f"Status: {r2.status_code}")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback; traceback.print_exc()

# 3. Stat page — show_all + segment
print("\n=== Test 3: obr_stat (with segment) ===")
req3 = rf.get('/obr/test/test/', {'show_all': '1', 'segment': 'Bodi kr/r (14900)'})
req3.user = u; req3.session = {}
try:
    r3 = obr_stat(req3, category='Новорождённый', subcategory='Боди')
    print(f"Status: {r3.status_code}")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback; traceback.print_exc()

# 4. Stat page — segment filter yo'q
print("\n=== Test 4: obr_stat (no segment) ===")
req4 = rf.get('/obr/test/test/', {'show_all': '1'})
req4.user = u; req4.session = {}
try:
    r4 = obr_stat(req4, category='Новорождённый', subcategory='Боди')
    print(f"Status: {r4.status_code}")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback; traceback.print_exc()
