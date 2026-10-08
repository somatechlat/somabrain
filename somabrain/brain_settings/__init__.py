"""Brain Settings - DB-Backed Configuration.

NO FALLBACKS. FAIL FAST. Tenant is required (T-5: no invented default).
Must run BrainSetting.initialize_defaults() before using.
"""

from typing import Any


def get(key: str, tenant: str) -> Any:
    """Lazy import and get setting. Tenant is required."""
    from .models import BrainSetting

    return BrainSetting.get(key, tenant)


def set(key: str, value: Any, tenant: str) -> None:
    """Lazy import and set setting. Tenant is required."""
    from .models import BrainSetting

    BrainSetting.set(key, value, tenant)


def initialize_defaults(tenant: str) -> int:
    """Lazy import and initialize defaults. Tenant is required."""
    from .models import BrainSetting

    return BrainSetting.initialize_defaults(tenant)


__all__ = [
    "get",
    "initialize_defaults",
    "set",
]
