"""Thin adapter to the runtime config service.

This provides stable helpers (get/get_bool/get_float/get_str) used by services
that need live configuration without importing the full runtime package tree.
It fails fast if the ConfigService is unavailable.
"""

from __future__ import annotations

from typing import Any, Optional

def _svc():
    try:
        from somabrain.runtime import config_runtime as _rt_impl

        svc = _rt_impl.get_config_service()
        if svc is None:
            raise RuntimeError("ConfigService unavailable")
        return svc
    except Exception as exc:
        raise RuntimeError("ConfigService unavailable") from exc


def get(key: str, default: Optional[Any] = None) -> Any:
    try:
        return _svc().effective_config("", "").get(key, default)
    except Exception:
        return default


def get_bool(key: str, default: bool = False) -> bool:
    try:
        val = get(key, default)
        if isinstance(val, bool):
            return val
        if isinstance(val, (int, float)):
            return bool(val)
        if isinstance(val, str):
            return val.strip().lower() in {"1", "true", "yes", "on"}
    except Exception:
        return default
    return default


def get_float(key: str, default: float = 0.0) -> float:
    try:
        val = get(key, default)
        return float(val)
    except Exception:
        return default


def get_str(key: str, default: str = "") -> str:
    try:
        val = get(key, default)
        return str(val)
    except Exception:
        return default
