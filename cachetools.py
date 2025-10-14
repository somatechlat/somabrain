"""Minimal TTL cache shim used across SomaBrain.

Historically the project depended on the third-party ``cachetools`` package, but
Sprint A0 migration exposed a recursive-import bug in the helper file that lived
in this repository.  The implementation below provides a tiny ``TTLCache``
compatible with the methods used in the codebase (``get`` / ``__getitem__`` /
``__setitem__`` / ``__contains__``) so we can keep deterministic behaviour even
when the external dependency is absent.

When the library is installed via `pip`/`uv`, Python will import the real
package (the shim is bypassed once the distribution is on `sys.path`).  During
editable development, however, the repository root sits at the front of
``sys.path``; this file therefore provides a deterministic fallback so imports
never fail.
"""

from __future__ import annotations

import time
from collections import OrderedDict
from typing import Iterator, MutableMapping, Tuple, TypeVar

__all__ = ["TTLCache"]

_VT = TypeVar("_VT")


class TTLCache(MutableMapping[str, _VT]):
    """Simple LRU-style cache with a fixed TTL for every entry."""

    def __init__(self, maxsize: int = 128, ttl: float = 600.0):
        if maxsize <= 0:
            raise ValueError("maxsize must be positive")
        if ttl <= 0:
            raise ValueError("ttl must be positive")
        self.maxsize = int(maxsize)
        self.ttl = float(ttl)
        self._store: "OrderedDict[str, Tuple[_VT, float]]" = OrderedDict()

    # Internal helpers -----------------------------------------------------
    def _now(self) -> float:
        return time.monotonic()

    def _evict_expired(self) -> None:
        now = self._now()
        expired = [key for key, (_, exp) in self._store.items() if exp <= now]
        for key in expired:
            self._store.pop(key, None)

    def _enforce_size(self) -> None:
        while len(self._store) > self.maxsize:
            self._store.popitem(last=False)

    # MutableMapping API ---------------------------------------------------
    def __getitem__(self, key: str) -> _VT:
        self._evict_expired()
        value, expiry = self._store[key]
        if expiry <= self._now():
            self._store.pop(key, None)
            raise KeyError(key)
        self._store.move_to_end(key, last=True)
        return value

    def __setitem__(self, key: str, value: _VT) -> None:
        self._evict_expired()
        self._store[key] = (value, self._now() + self.ttl)
        self._store.move_to_end(key, last=True)
        self._enforce_size()

    def __delitem__(self, key: str) -> None:
        self._store.pop(key)

    def __iter__(self) -> Iterator[str]:
        self._evict_expired()
        return iter(list(self._store.keys()))

    def __len__(self) -> int:
        self._evict_expired()
        return len(self._store)

    # Convenience helpers --------------------------------------------------
    def get(self, key: str, default: _VT | None = None) -> _VT | None:  # type: ignore[override]
        try:
            return self[key]
        except KeyError:
            return default

    def clear(self) -> None:  # pragma: no cover - mirrors dict API
        self._store.clear()

    def pop(self, key: str, default: _VT | None = None) -> _VT | None:  # type: ignore[override]
        self._evict_expired()
        try:
            value, _ = self._store.pop(key)
            return value
        except KeyError:
            return default
