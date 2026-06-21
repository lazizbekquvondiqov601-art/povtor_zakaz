"""Debug script to capture exact SQL/params causing TypeError in last_executed_query."""
import os
import sys
import traceback

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'panel_config.settings')

import django
django.setup()

from django.db.backends.sqlite3 import operations

orig_leq = operations.DatabaseOperations.last_executed_query
orig_quote = operations.DatabaseOperations._quote_params_for_last_executed_query


def debug_quote(self, params):
    print(f"[QUOTE] params type={type(params).__name__} len={len(params)} value={params!r}")
    try:
        result = orig_quote(self, params)
        print(f"[QUOTE] result type={type(result).__name__} value={result!r}")
        if result is not None:
            print(f"[QUOTE] result len={len(result)}")
        return result
    except Exception as e:
        print(f"[QUOTE] EXCEPTION: {type(e).__name__}: {e}")
        raise


def debug_leq(self, cursor, sql, params):
    print("=" * 80)
    print(f"[LEQ] SQL: {sql!r}")
    print(f"[LEQ] PARAMS type={type(params).__name__} value={params!r}")
    if params is not None:
        try:
            print(f"[LEQ] PARAMS len={len(params)}")
        except TypeError:
            print("[LEQ] PARAMS no len")
        print(f"[LEQ] SQL %s count = {sql.count('%s')}")
    try:
        result = debug_leq_inner(self, cursor, sql, params)
        return result
    except TypeError as e:
        print(f"[LEQ] TypeError: {e}")
        traceback.print_exc()
        raise


def debug_leq_inner(self, cursor, sql, params):
    if params:
        if isinstance(params, (list, tuple)):
            quoted = debug_quote(self, params)
            print(f"[LEQ-INNER] About to do sql % quoted; quoted={quoted!r}")
            return sql % quoted
        else:
            values = tuple(params.values())
            quoted = debug_quote(self, values)
            params = dict(zip(params, quoted))
            return sql % params
    else:
        return sql


operations.DatabaseOperations.last_executed_query = debug_leq
operations.DatabaseOperations._quote_params_for_last_executed_query = debug_quote

# Now create test user and try login
from django.contrib.auth import get_user_model
User = get_user_model()
try:
    if not User.objects.filter(username='debugadmin').exists():
        User.objects.create_superuser('debugadmin', 'a@a.com', 'debugpass1234')
        print("[SETUP] created debugadmin")
except Exception as e:
    print(f"[SETUP] user create skipped: {e}")

from django.test import Client
c = Client()
ok = c.login(username='debugadmin', password='debugpass1234')
print(f"[SETUP] login ok={ok}")

print("\n\n>>>>>>>>>>>>>> GET / <<<<<<<<<<<<<<<\n")
try:
    resp = c.get('/')
    print(f"[RESULT] status={resp.status_code}")
except Exception as e:
    print(f"[RESULT] EXCEPTION: {type(e).__name__}: {e}")
    traceback.print_exc()
