"""Helpers for allocating free host ports for local stacks."""

from __future__ import annotations

from common.config.settings import settings
import socket
from typing import Dict


def _env_port(name: str, default_val: int) -> int:
    """Get port from environment or return default value."""
    try:
        # Retrieve the setting via attribute lookup; fallback to None if missing.
        raw = getattr(settings, name.lower(), None)
        if not raw:
            return default_val
        return int(raw)
    except Exception:
        return default_val


DEFAULT_SERVICE_PORTS: Dict[str, int] = {
    "SOMABRAIN_HOST_PORT": _env_port("SOMABRAIN_HOST_PORT", 9696),
    # canonical host port for local somabrain API
    "REDIS_HOST_PORT": _env_port("REDIS_HOST_PORT", 6379),
    "KAFKA_HOST_PORT": _env_port("KAFKA_BROKER_HOST_PORT", 9092),
    "PROMETHEUS_HOST_PORT": _env_port("PROMETHEUS_HOST_PORT", 9090),
    "POSTGRES_HOST_PORT": _env_port("POSTGRES_HOST_PORT", 15432),
    "SOMAMEMORY_HOST_PORT": _env_port("SOMABRAIN_MEMORY_HTTP_PORT", 9595),
}


def is_port_free(port: int, host: str = "127.0.0.1") -> bool:
    hosts = {host, "0.0.0.0"}
    for entry in hosts:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind((entry, port))
            except OSError:
                return False
    return True


def pick_free_port(start: int, host: str = "127.0.0.1", attempts: int = 1000) -> int:
    for offset in range(attempts):
        candidate = start + offset
        if is_port_free(candidate, host=host):
            return candidate
    raise RuntimeError(f"No free port found in range starting at {start}")


def allocate_ports(defaults: Dict[str, int] | None = None) -> Dict[str, int]:
    defaults = defaults or DEFAULT_SERVICE_PORTS
    allocation: Dict[str, int] = {}
    for key, base in defaults.items():
        port = pick_free_port(base)
        allocation[key] = port
    return allocation


__all__ = ["allocate_ports", "pick_free_port", "is_port_free", "DEFAULT_SERVICE_PORTS"]
