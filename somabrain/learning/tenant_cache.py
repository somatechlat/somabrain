"""Tenant overrides cache for per-tenant learning configuration.

This module provides caching for tenant-specific learning configuration
overrides that can be loaded from YAML/JSON files or environment variables.
"""

from __future__ import annotations

import json
import os
from typing import Dict

try:
    from django.conf import settings
except Exception:  # pragma: no cover - optional dependency
    settings = None

from somabrain.core.container import container


class TenantOverridesCache:
    """Cache for per-tenant configuration overrides.

    This class encapsulates the caching logic for tenant-specific learning
    configuration overrides. Overrides can be loaded from a YAML/JSON file
    or from an environment variable.

    Cache Invalidation:
        The cache is invalidated when the configured file path changes.
        Call clear() to force a reload on next access.
    """

    def __init__(self) -> None:
        self._overrides: Dict[str, dict] | None = None
        self._path: str | None = None

    def load(self) -> Dict[str, dict]:
        """Load tenant overrides from file or environment.

        Returns cached overrides if available and path hasn't changed.
        """
        path = getattr(settings, "learning_tenants_file", None) if settings else None
        # Reload if cache empty or path changed
        if self._overrides is not None and path == self._path:
            return self._overrides

        overrides: Dict[str, dict] = {}
        # Attempt to load from YAML if available
        if path and os.path.exists(path):
            try:
                import yaml

                with open(path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                if isinstance(data, dict):
                    overrides = {
                        str(k): (v or {})
                        for k, v in data.items()
                        if isinstance(v, dict)
                    }
            except Exception:
                # Fallback to JSON parse if YAML not available or fails
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if isinstance(data, dict):
                        overrides = {
                            str(k): (v or {})
                            for k, v in data.items()
                            if isinstance(v, dict)
                        }
                except Exception:
                    overrides = {}

        # Optional: overrides via env JSON string
        if not overrides:
            raw = (
                getattr(settings, "learning_tenants_overrides", "") if settings else ""
            )
            raw = (raw or "").strip()
            if raw:
                try:
                    data = json.loads(raw)
                    if isinstance(data, dict):
                        overrides = {
                            str(k): (v or {})
                            for k, v in data.items()
                            if isinstance(v, dict)
                        }
                except Exception:
                    overrides = {}

        self._overrides = overrides
        self._path = path
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


def load_tenant_overrides() -> Dict[str, dict]:
    """Load tenant overrides from cache."""
    return get_tenant_overrides_cache().load()


def get_tenant_override(tenant_id: str) -> dict:
    """Get overrides for a specific tenant."""
    return get_tenant_overrides_cache().get(tenant_id)
