from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional

from somabrain.runtime import config_runtime as _rt_impl


def _effective() -> Dict[str, Any]:
    svc = _rt_impl.get_config_service()
    if svc is None:
        raise RuntimeError("ConfigService unavailable")
    return svc.effective_config("", "")


def get(key: str, default: Optional[Any] = None) -> Any:
    try:
        return _effective().get(key, default)
    except Exception:
        return default


def get_bool(key: str, default: bool = False) -> bool:
    try:
        val = _effective().get(key, default)
        if isinstance(val, bool):
            return val
        if isinstance(val, (int, float)):
            return bool(val)
        if isinstance(val, str):
            return val.strip().lower() in ("1", "true", "yes", "on")
    except Exception:
        return default
    return default


def get_float(key: str, default: float = 0.0) -> float:
    try:
        val = _effective().get(key, default)
        return float(val)
    except Exception:
        return default


def get_str(key: str, default: str = "") -> str:
    try:
        val = _effective().get(key, default)
        return str(val)
    except Exception:
        return default


def set_overrides(updates: Dict[str, Any]) -> None:
    """Patch global config via ConfigService (synchronous wrapper).

    Raises if called inside a running event loop; prefer async patching in that case.
    """
    if not isinstance(updates, dict):
        raise ValueError("updates must be a dict")
    loop = None
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    async def _patch() -> None:
        svc = _rt_impl.get_config_service()
        await svc.patch_global(updates, actor="runtime_config.set_overrides")

    if loop and loop.is_running():
        raise RuntimeError("set_overrides cannot run inside an active event loop; use config_runtime directly")
    asyncio.run(_patch())
