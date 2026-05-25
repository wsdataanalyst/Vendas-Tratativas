import time
from typing import Any

_store: dict[str, tuple[float, Any]] = {}
TTL = 8.0


def get(key: str, factory):
    now = time.time()
    if key in _store:
        ts, val = _store[key]
        if now - ts < TTL:
            return val
    val = factory()
    _store[key] = (now, val)
    return val


def invalidate(*prefixes: str):
    if not prefixes:
        _store.clear()
        return
    for k in list(_store):
        if any(k.startswith(p) for p in prefixes):
            del _store[k]
