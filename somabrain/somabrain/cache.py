from __future__ import annotations

import time
from collections import OrderedDict
from typing import Any, Tuple


class TTLCache:
    def __init__(self, maxsize: int = 1024, ttl: float = 2.0):
        self.maxsize = int(maxsize)
        self.ttl = float(ttl)
        self._data: OrderedDict[str, Tuple[float, Any]] = OrderedDict()

    def get(self, key: str):
        now = time.monotonic()
        item = self._data.get(key)
        if not item:
            return None
        ts, val = item
        if now - ts > self.ttl:
            self._data.pop(key, None)
            return None
        self._data.move_to_end(key)
        return val

    def set(self, key: str, val: Any):
        now = time.monotonic()
        self._data[key] = (now, val)
        self._data.move_to_end(key)
        while len(self._data) > self.maxsize:
            self._data.popitem(last=False)

