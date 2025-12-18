"""Auth dependency wiring for FastAPI routes.

This module now integrates with the centralized tenant management system
to provide dynamic tenant resolution and validation.
"""

from __future__ import annotations

from common.config.settings import settings
from pathlib import Path
from typing import List, Optional


# Legacy Config model replaced by unified Settings
from common.config.settings import Settings as Config

_current_config: Optional[Config] = None
_allowed_tenants: List[str] = []
_default_tenant: str = getattr(settings, "default_tenant", "sandbox")


def set_auth_config(cfg: Config) -> None:
    """Register configuration for downstream auth + tenant helpers.

    Note: This method is deprecated. Use the centralized tenant management system
    through TenantManager instead.
    """
    global _current_config, _allowed_tenants, _default_tenant
    _current_config = cfg
    _default_tenant = cfg.default_tenant or getattr(
        settings, "default_tenant", "sandbox"
    )
    _allowed_tenants = _resolve_tenants(cfg)


def _resolve_tenants(cfg: Config) -> List[str]:
    tenants: List[str] = []
    # From config list
    if getattr(cfg, "sandbox_tenants", None):
        tenants.extend(str(t).strip() for t in cfg.sandbox_tenants if str(t).strip())
    # From env comma-separated list
    env_tenants = getattr(settings, "sandbox_tenants", None)
    if env_tenants:
        tenants.extend(t.strip() for t in env_tenants.split(",") if t.strip())
    # From optional file (YAML list or dict with tenants/allowed)
    file_path = cfg.sandbox_tenants_file or getattr(
        settings, "sandbox_tenants_file", None
    )
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


def auth_override_disabled() -> None:
    """Utility for tests wanting to disable auth."""
    global _current_config
    _current_config = None


# Note: auth_guard, get_allowed_tenants_async, and get_default_tenant_async
# have been removed. Use TenantManager directly for tenant resolution:
#
#   from somabrain.tenant_manager import get_tenant_manager
#   tenant_manager = await get_tenant_manager()
#   tenant_id = await tenant_manager.resolve_tenant_from_request(request)
#   tenants = await tenant_manager.list_tenants()
