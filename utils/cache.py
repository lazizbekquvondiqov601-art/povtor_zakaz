import time

class TTLCache:
    def __init__(self, ttl=1800):
        self._store = {}
        self.ttl = ttl

    def set(self, key, value):
        self._store[key] = (value, time.monotonic())

    def get(self, key, default=None):
        item = self._store.get(key)
        if item is None:
            return default
        value, ts = item
        if time.monotonic() - ts > self.ttl:
            del self._store[key]
            return default
        return value

    def __setitem__(self, key, value):
        self.set(key, value)

    def __getitem__(self, key):
        r = self.get(key)
        if r is None:
            raise KeyError(key)
        return r

    def __contains__(self, key):
        return self.get(key) is not None

    def cleanup(self):
        now = time.monotonic()
        expired = [k for k, (_, ts) in self._store.items() if now - ts > self.ttl]
        for k in expired:
            del self._store[k]

    def __len__(self):
        return len(self._store)

OBR_CACHE = TTLCache(ttl=1800)
STAT_CACHE = TTLCache(ttl=1800)
