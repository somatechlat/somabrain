"""Auth dependency wiring for FastAPI routes.

This module now integrates with the centralized tenant management system
to provide dynamic tenant resolution and validation.
"""

from __future__ import annotations

from common.config.settings import settings
from pathlib import Path
from typing import List, Optional

from fastapi import Request

from somabrain.auth import require_auth
# Legacy Config model replaced by unified Settings
from common.config.settings import Settings as Config

_current_config: Optional[Config] = None
_allowed_tenants: List[str] = []
_default_tenant: str = "sandbox"  # DEPRECATED: Use tenant_registry instead


def set_auth_config(cfg: Config) -> None:
    """Register configuration for downstream auth + tenant helpers.
    
    Note: This method is deprecated. Use the centralized tenant management system
    through TenantManager instead.
    """
    global _current_config, _allowed_tenants, _default_tenant
    _current_config = cfg
    _default_tenant = cfg.default_tenant or settings.getenv(
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
    env_tenants = settings.getenv("SOMABRAIN_SANDBOX_TENANTS")
    if env_tenants:
        tenants.extend(t.strip() for t in env_tenants.split(",") if t.strip())
    # From optional file (YAML list or dict with tenants/allowed)
    file_path = cfg.sandbox_tenants_file or settings.getenv("SOMABRAIN_SANDBOX_TENANTS_FILE")
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
    """Get list of allowed tenants (DEPRECATED).
    
    This method is deprecated. Use TenantManager.list_tenants() instead.
    """
    return list(_allowed_tenants)


def get_default_tenant() -> str:
    """Get default tenant ID (DEPRECATED).
    
    This method is deprecated. Use TenantManager.resolve_tenant_from_request() instead.
    """
    return _default_tenant


def auth_override_disabled() -> None:
    """Utility for tests wanting to disable auth."""
    global _current_config
    _current_config = None


async def auth_guard(request: Request) -> None:
    """Auth guard with tenant validation (DEPRECATED).
    
    This method is deprecated. Use centralized tenant management through TenantManager.
    """
    if _current_config is None:
        return
    require_auth(request, _current_config)


async def get_allowed_tenants_async() -> List[str]:
    """Get list of allowed tenants using centralized tenant management."""
    try:
        from somabrain.tenant_manager import get_tenant_manager
        tenant_manager = await get_tenant_manager()
        tenants = await tenant_manager.list_tenants()
        return [t.tenant_id for t in tenants if t.status.value == "active"]
    except Exception:
        # Fallback to legacy method
        return get_allowed_tenants()


async def get_default_tenant_async() -> str:
    """Get default tenant ID using centralized tenant management."""
    try:
        from somabrain.tenant_manager import get_tenant_manager
        tenant_manager = await get_tenant_manager()
        
        # Try to get public tenant
        public_tenant_id = await tenant_manager.get_system_tenant_id("public")
        if public_tenant_id:
            return public_tenant_id
        
        # Fallback to legacy method
        return get_default_tenant()
    except Exception:
        return get_default_tenant()
