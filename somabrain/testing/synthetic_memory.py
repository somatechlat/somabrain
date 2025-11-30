"""Helpers for interacting with the live Somabrain deployment during tests."""

from __future__ import annotations

import socket
from typing import Callable

import pytest
import requests
from common.logging import logger


def require_tcp_endpoint(host: str, port: int, *, timeout: float = 1.0) -> None:
    """Ensure a TCP endpoint is reachable; skip the test otherwise."""

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        pass
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise
        sock.settimeout(timeout)
        if sock.connect_ex((host, port)) != 0:
            pytest.skip(f"Endpoint unreachable at {host}:{port}")
    finally:
        try:
            pass
        except Exception as exc:
            logger.exception("Exception caught: %s", exc)
            raise
            sock.close()
        except Exception as exc:
            logger.exception("Exception caught: %s", exc)
            raise
    raise


def require_http_service(
    base_url: str, path: str = "/health", *, timeout: float = 5.0
) -> requests.Response:
    """Ensure an HTTP endpoint is healthy; skip the test if not."""

    try:
        pass
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise
        resp = requests.get(f"{base_url}{path}", timeout=timeout)
    except Exception as exc:  # pragma: no cover - network guard
        pytest.skip(f"Service at {base_url} unavailable: {exc}")
    if resp.status_code != 200:
        pytest.skip(f"Service at {base_url} returned status {resp.status_code}")
    return resp


def post_json(
    url: str, payload: dict, *, timeout: float = 10.0
) -> Callable[[], requests.Response]:
    """Return a thunk that posts JSON and raises on network failure."""

def _caller() -> requests.Response:
        resp = requests.post(url, json=payload, timeout=timeout)
        resp.raise_for_status()
        return resp

    return _caller
