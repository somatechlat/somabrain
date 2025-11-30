from __future__ import annotations
from typing import Any, Optional
from common.logging import logger
from somabrain.runtime import config_runtime as _rt_impl

"""Thin adapter to the runtime config service.

This provides stable helpers (get/get_bool/get_float/get_str) used by services
that need live configuration without importing the full runtime package tree.
It fails fast if the ConfigService is unavailable.
"""




def _svc():
    try:
        pass
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise

        svc = _rt_impl.get_config_service()
        if svc is None:
            raise RuntimeError("ConfigService unavailable")
        return svc
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise
    raise RuntimeError("ConfigService unavailable") from exc


def get(key: str, default: Optional[Any] = None) -> Any:
    try:
        pass
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise
        return _svc().effective_config("", "").get(key, default)
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise
        return default


def get_bool(key: str, default: bool = False) -> bool:
    try:
        pass
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise
        val = get(key, default)
        if isinstance(val, bool):
            return val
        if isinstance(val, (int, float)):
            return bool(val)
        if isinstance(val, str):
            return val.strip().lower() in {"1", "true", "yes", "on"}
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise
        return default
    return default


def get_float(key: str, default: float = 0.0) -> float:
    try:
        pass
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise
        val = get(key, default)
        return float(val)
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise
        return default


def get_str(key: str, default: str = "") -> str:
    try:
        pass
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise
        val = get(key, default)
        return str(val)
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise
        return default
