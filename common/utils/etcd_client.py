"""Thin Etcd client used for feature-flag distribution."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Callable, Generator, Optional

# Track import error for optional dependency
_import_error: Exception | None = None
try:  # pragma: no cover - optional dependency
    import etcd3
except Exception as exc:  # pragma: no cover
    etcd3 = None
    _import_error = exc


class EtcdClient:
    """Wrapper around ``etcd3.client`` with typed helpers."""

    def __init__(self, host: str = "etcd", port: int = 2379, timeout: float = 5.0):
        if etcd3 is None:  # pragma: no cover - executed when dependency missing
            raise RuntimeError(
                "etcd3 package not available; install it or disable Etcd integration"
            ) from _import_error
        self._client = etcd3.client(host=host, port=port, timeout=timeout)

    def get_flag(self, key: str) -> Optional[str]:
        value, _ = self._client.get(key)
        if value is None:
            return None
        return value.decode("utf-8") if isinstance(value, bytes) else str(value)

    def set_flag(self, key: str, value: str) -> None:
        self._client.put(key, value)

    def delete_flag(self, key: str) -> None:
        self._client.delete(key)

    @contextmanager
    def watch_prefix(
        self, prefix: str, callback: Callable[[str, Optional[str]], Any]
    ) -> Generator[None, None, None]:
        """Watch a prefix and invoke ``callback`` for every update."""

        def _handler(event):
            if event.value is None:
                payload = None
            else:
                payload = (
                    event.value.decode("utf-8")
                    if isinstance(event.value, bytes)
                    else str(event.value)
                )
            callback(event.key.decode("utf-8"), payload)

        watch_id = self._client.add_watch_prefix_callback(prefix, _handler)
        try:
            yield
        finally:
            self._client.cancel_watch(watch_id)


__all__ = ["EtcdClient"]
