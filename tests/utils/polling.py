"""Lightweight polling helpers to replace fixed sleeps in tests.

Usage examples
--------------

- Wait for a condition:
    >>> from tests.utils.polling import wait_for
    >>> wait_for(lambda: cache.get("ready") is not None, timeout=3)

- Wait for HTTP 200 OK:
    >>> from tests.utils.polling import wait_for_http
    >>> wait_for_http("http://localhost:9696/health", expect=200, timeout=5)

- Async condition:
    >>> import asyncio
    >>> from tests.utils.polling import async_wait_for
    >>> async def is_ready():
    ...     return await some_async_check()
    >>> asyncio.run(async_wait_for(is_ready, timeout=2))
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Callable, Iterable, Optional, Union

try:
    import requests
    from requests import Response
except Exception:  # pragma: no cover - requests present in dev deps
    requests = None  # type: ignore
    Response = Any  # type: ignore


Predicate = Callable[[], Union[bool, Any]]


def wait_for(
    predicate: Predicate,
    *,
    timeout: float = 5.0,
    interval: float = 0.05,
    desc: Optional[str] = None,
    swallow: Iterable[type[BaseException]] = (Exception,),
) -> bool:
    """Poll `predicate` until truthy or timeout.

    - `interval`: sleep between attempts
    - `swallow`: exception types to ignore while polling
    - Returns True if condition met; raises TimeoutError otherwise
    """

    start = time.monotonic()
    last_exc: Optional[BaseException] = None
    while True:
        try:
            if predicate():
                return True
        except tuple(swallow) as e:  # type: ignore[arg-type]
            last_exc = e
        if time.monotonic() - start >= timeout:
            details = f" after {timeout:.2f}s"
            if desc:
                details = f" waiting for {desc}{details}"
            if last_exc is not None:
                details = f"{details} (last error: {last_exc})"
            raise TimeoutError(f"Condition not met{details}")
        time.sleep(interval)


async def async_wait_for(
    predicate: Predicate,
    *,
    timeout: float = 5.0,
    interval: float = 0.05,
    desc: Optional[str] = None,
) -> bool:
    """Async variant of `wait_for`.

    Supports a synchronous or awaitable predicate.
    """

    start = time.monotonic()
    while True:
        result = predicate()
        if asyncio.iscoroutine(result):
            result = await result  # type: ignore[assignment]
        if result:
            return True
        if time.monotonic() - start >= timeout:
            details = f" after {timeout:.2f}s"
            if desc:
                details = f" waiting for {desc}{details}"
            raise TimeoutError(f"Condition not met{details}")
        await asyncio.sleep(interval)


def wait_for_http(
    url: str,
    *,
    expect: Union[int, Callable[[Response], bool]] = 200,
    method: str = "GET",
    timeout: float = 5.0,
    interval: float = 0.1,
    **request_kwargs: Any,
) -> Response:
    """Poll an HTTP endpoint until it returns the expected condition.

    - `expect`: status code (int) or callable `(Response) -> bool`
    - Returns the final `requests.Response` if condition satisfied
    - Raises `TimeoutError` if not satisfied within `timeout`
    """

    if requests is None:  # pragma: no cover
        raise RuntimeError("requests is required for wait_for_http; install dev deps")

    start = time.monotonic()
    last_exc: Optional[BaseException] = None
    while True:
        try:
            resp = requests.request(method, url, timeout=min(interval, 2.0), **request_kwargs)
            ok = resp.status_code == expect if isinstance(expect, int) else bool(expect(resp))
            if ok:
                return resp
        except Exception as e:  # swallow transient connect errors while polling
            last_exc = e
        if time.monotonic() - start >= timeout:
            detail = f"status {getattr(resp, 'status_code', 'n/a')}" if 'resp' in locals() else "no response"
            extra = f"; last error: {last_exc}" if last_exc else ""
            raise TimeoutError(f"HTTP condition not met for {url} ({detail}) after {timeout:.2f}s{extra}")
        time.sleep(interval)


__all__ = ["wait_for", "async_wait_for", "wait_for_http"]
