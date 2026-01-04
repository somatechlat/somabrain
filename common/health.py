"""Module health."""

from __future__ import annotations

"""Utility module for simple health-check HTTP calls.

The project contains a number of ad‑hoc ``requests`` calls scattered throughout
scripts and services to verify that external services are reachable. The VIBE
coding rules require a single, reusable helper for this purpose.

Usage::

    from common.health import check_health
    if check_health(settings.SOMABRAIN_MEMORY_HTTP_ENDPOINT):
        ...

The function returns ``True`` when a ``GET`` request succeeds with a ``200``
status code, otherwise ``False``. A short timeout (default 2 seconds) is used
to avoid hanging the caller. ``requests`` is optional – if it cannot be
imported the implementation falls back to ``urllib.request`` from the standard
library.
"""

import urllib.request
from typing import Optional

try:
    import requests
except Exception:  # pragma: no cover – ``requests`` may be unavailable in minimal envs.
    requests = None


def _http_get(url: str, timeout: float) -> Optional[int]:
    """Perform a ``GET`` request and return the HTTP status code.

    The helper abstracts the difference between ``requests`` and ``urllib`` so
    callers only need to handle the ``None`` case (indicating a failure to
    perform the request).
    """
    if not url:
        return None
    if requests is not None:
        try:
            resp = requests.get(url, timeout=timeout)
            return resp.status_code
        except Exception:
            return None
    # Fallback to urllib
    try:
        with urllib.request.urlopen(
            url, timeout=timeout
        ) as resp:  # noqa: S310 – URL is provided by caller.
            return resp.getcode()
    except Exception:
        return None


def check_health(url: str, *, timeout: float = 2.0) -> bool:
    """Return ``True`` if the endpoint at *url* responds with HTTP 200.

    Parameters
    ----------
    url:
        The full URL to query (including scheme and path).
    timeout:
        Maximum seconds to wait for a response. Defaults to ``2.0`` seconds.
    """
    status = _http_get(url, timeout)
    return status == 200