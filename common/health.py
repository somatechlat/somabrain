"""Simple health‑check utility.

Provides a tiny wrapper around ``requests.get`` that returns ``True`` when the
target URL responds with a successful (2xx) HTTP status code and ``False``
otherwise.  The function is deliberately lightweight – it catches any
exception (network error, timeout, etc.) and treats it as an unhealthy result.

This helper is used by services that expose a ``/health`` endpoint (e.g.
``somabrain.services.integrator_hub_triplet``) to perform a quick liveness
probe without pulling in the full FastAPI machinery.
"""

from __future__ import annotations

from typing import Final

import requests

DEFAULT_TIMEOUT: Final = 2.0  # seconds – reasonable default for a health probe


def check_health(url: str, timeout: float = DEFAULT_TIMEOUT) -> bool:
    """Return ``True`` if an HTTP GET to *url* succeeds (status code 2xx).

    Args:
        url: The full URL to query (including scheme and host).
        timeout: Maximum time to wait for a response, in seconds.

    The function catches *all* exceptions and returns ``False`` – the caller
    can treat any ``False`` result as an indication that the service is not
    healthy.
    """
    try:
        response = requests.get(url, timeout=timeout)
        return response.ok
    except Exception:
        return False


"""Utility module for simple health‑check HTTP calls.

The project contains a number of ad‑hoc ``requests`` calls scattered throughout
scripts and services to verify that external services are reachable.  The VIBE
coding rules require a single, reusable helper for this purpose.

Usage::

    from common.health import check_health
    if check_health(settings.memory_http_endpoint):
        ...

The function returns ``True`` when a ``GET`` request succeeds with a ``200``
status code, otherwise ``False``.  A short timeout (default 2 seconds) is used
to avoid hanging the caller.  ``requests`` is optional – if it cannot be
imported the implementation falls back to ``urllib.request`` from the standard
library.
"""

from __future__ import annotations

import urllib.request
from typing import Optional

try:
    import requests  # type: ignore
except Exception:  # pragma: no cover – ``requests`` may be unavailable in minimal envs.
    requests = None  # type: ignore


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
        Maximum seconds to wait for a response.  Defaults to ``2.0`` seconds.
    """
    status = _http_get(url, timeout)
    return status == 200
