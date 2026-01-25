"""
SSO Identity Provider Storage.

Cache-based IdP storage with CRUD operations.

ALL 10 PERSONAS:
- 📊 Perf: Cached IdP config
- 🔒 Security: Secure storage
"""

from typing import List, Optional
from uuid import uuid4

from django.core.cache import cache
from django.utils import timezone

from .schemas import IdPStatus


def get_idps_key(tenant_id: str) -> str:
    """Get cache key for tenant IdP list."""
    return f"idps:tenant:{tenant_id}"


def get_idp_key(idp_id: str) -> str:
    """Get cache key for IdP."""
    return f"idp:{idp_id}"


def create_idp(tenant_id: str, name: str, provider_type: str, config: dict, created_by: str) -> dict:
    """Create a new identity provider."""
    idp_id = str(uuid4())
    idp = {
        "id": idp_id,
        "tenant_id": tenant_id,
        "name": name,
        "type": provider_type,
        "status": IdPStatus.TESTING,
        "config": config,
        "created_by": created_by,
        "created_at": timezone.now().isoformat(),
        "last_verified_at": None,
        "login_count": 0,
        "error_count": 0,
        "last_error": None,
    }
    cache.set(get_idp_key(idp_id), idp, timeout=86400 * 30)
    tenant_key = get_idps_key(tenant_id)
    idps = cache.get(tenant_key, [])
    idps.append(idp_id)
    cache.set(tenant_key, idps, timeout=86400 * 30)
    return idp


def get_idp(idp_id: str) -> Optional[dict]:
    """Get IdP by ID."""
    return cache.get(get_idp_key(idp_id))


def update_idp(idp_id: str, **updates) -> Optional[dict]:
    """Update IdP fields."""
    key = get_idp_key(idp_id)
    idp = cache.get(key)
    if idp:
        idp.update(updates)
        cache.set(key, idp, timeout=86400 * 30)
    return idp


def get_tenant_idps(tenant_id: str) -> List[dict]:
    """Get all IdPs for a tenant."""
    idp_ids = cache.get(get_idps_key(tenant_id), [])
    idps = []
    for iid in idp_ids:
        idp = get_idp(iid)
        if idp:
            idps.append(idp)
    return idps


def delete_idp(idp_id: str, tenant_id: str) -> bool:
    """Delete IdP from cache."""
    cache.delete(get_idp_key(idp_id))
    tenant_key = get_idps_key(tenant_id)
    idps = cache.get(tenant_key, [])
    idps = [i for i in idps if i != idp_id]
    cache.set(tenant_key, idps, timeout=86400 * 30)
    return True


def mask_sensitive_config(config: dict) -> dict:
    """Mask sensitive values in config."""
    masked = config.copy()
    for key in ["client_secret", "certificate", "bind_password", "password"]:
        if key in masked:
            masked[key] = "********"
    return masked
