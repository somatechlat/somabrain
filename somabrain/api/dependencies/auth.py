"""Auth dependency wiring for FastAPI routes."""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional

from fastapi import Request

from somabrain.auth import require_auth
from somabrain.config import Config

_current_config: Optional[Config] = None
_allowed_tenants: List[str] = []
_default_tenant: str = "sandbox"


def set_auth_config(cfg: Config) -> None:
    """Register configuration for downstream auth + tenant helpers."""
    global _current_config, _allowed_tenants, _default_tenant
    _current_config = cfg
    _default_tenant = cfg.default_tenant or os.getenv(
        "SOMABRAIN_DEFAULT_TENANT", "sandbox"
    )
    os.environ.setdefault("SOMABRAIN_DEFAULT_TENANT", _default_tenant)
    _allowed_tenants = _resolve_tenants(cfg)


def _resolve_tenants(cfg: Config) -> List[str]:
    tenants: List[str] = []
    # From config list
    if getattr(cfg, "sandbox_tenants", None):
        tenants.extend(str(t).strip() for t in cfg.sandbox_tenants if str(t).strip())
    # From env comma-separated list
    env_tenants = os.getenv("SOMABRAIN_SANDBOX_TENANTS")
    if env_tenants:
        tenants.extend(t.strip() for t in env_tenants.split(",") if t.strip())
    # From optional file (YAML list or dict with tenants/allowed)
    file_path = cfg.sandbox_tenants_file or os.getenv("SOMABRAIN_SANDBOX_TENANTS_FILE")
    if file_path:
        p = Path(file_path)
        if p.exists():
            try:
                import yaml

                data = yaml.safe_load(p.read_text())
                if isinstance(data, dict):
                    vals = data.get("tenants") or data.get("allowed")
                    if isinstance(vals, list):
                        tenants.extend(str(t).strip() for t in vals if str(t).strip())
                elif isinstance(data, list):
                    tenants.extend(str(t).strip() for t in data if str(t).strip())
            except Exception:
                pass
    return sorted(set(t for t in tenants if t))


def get_allowed_tenants() -> List[str]:
    return list(_allowed_tenants)


def get_default_tenant() -> str:
    return _default_tenant


def auth_override_disabled() -> None:
    """Utility for tests wanting to disable auth."""
    global _current_config
    _current_config = None


async def auth_guard(request: Request) -> None:
    if _current_config is None:
        return
    require_auth(request, _current_config)
