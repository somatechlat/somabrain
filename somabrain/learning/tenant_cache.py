"""Tenant overrides cache for per-tenant learning configuration.

Operator law (Covenant Art 26 + VIBE): NO file presets. Overrides come from
BrainSetting (DB, administerable) or Django settings only.
"""

from __future__ import annotations

import json

try:
    from django.conf import settings
except Exception:  # pragma: no cover - optional dependency
    settings = None

from somabrain.core.container import container


class TenantOverridesCache:
    """Cache for per-tenant configuration overrides (DB / Django only)."""

    def __init__(self) -> None:
        """Initialize the instance."""

        self._overrides: dict[str, dict] | None = None

    def load(self) -> dict[str, dict]:
        """Load tenant overrides from BrainSetting (DB) then Django settings.

        Files are never read (Operator: settings must be administerable).
        """
        if self._overrides is not None:
            return self._overrides

        overrides: dict[str, dict] = {}
        try:
            from somabrain.brain_settings.models import BrainSetting

            for key in (
                "retrieval_alpha",
                "retrieval_beta",
                "retrieval_gamma",
                "retrieval_tau",
                "entropy_cap",
                "adapt_lr",
                "density_target",
                "density_floor",
                "density_weight",
            ):
                try:
                    value = BrainSetting.get(key, None)
                except Exception:
                    continue
                if value is None:
                    continue
                overrides.setdefault("default", {})[key] = value
        except Exception:
            pass

        raw = ""
        try:
            raw = str(getattr(settings, "LEARNING_TENANTS_OVERRIDES", "") or "").strip()
        except Exception:
            raw = ""
        if raw:
            try:
                data = json.loads(raw)
                if isinstance(data, dict):
                    for k, v in data.items():
                        if isinstance(v, dict):
                            overrides[str(k)] = {**overrides.get(str(k), {}), **v}
            except Exception:
                pass

        self._overrides = overrides
        return overrides

    def get(self, tenant_id: str) -> dict:
        """Get overrides for a specific tenant."""
        try:
            ov = self.load()
            return ov.get(str(tenant_id), {})
        except Exception:
            return {}

    def clear(self) -> None:
        """Clear the cache to force reload on next access."""
        self._overrides = None
        self._path = None


def _create_tenant_overrides_cache() -> TenantOverridesCache:
    """Factory function for DI container registration."""
    return TenantOverridesCache()


# Register with DI container
container.register("tenant_overrides_cache", _create_tenant_overrides_cache)


def get_tenant_overrides_cache() -> TenantOverridesCache:
    """Get the tenant overrides cache from the DI container."""
    return container.get("tenant_overrides_cache")


def load_tenant_overrides() -> dict[str, dict]:
    """Load tenant overrides from cache."""
    return get_tenant_overrides_cache().load()


def get_tenant_override(tenant_id: str) -> dict:
    """Get overrides for a specific tenant."""
    return get_tenant_overrides_cache().get(tenant_id)
