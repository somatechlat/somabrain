"""Brain Settings - DB-Backed Configuration.

NO FALLBACKS. FAIL FAST.
Must run BrainSetting.initialize_defaults() before using.
"""

from typing import Any


def get(key: str, tenant: str = "default") -> Any:
    """Lazy import and get setting."""
    from .models import BrainSetting
    return BrainSetting.get(key, tenant)


def set(key: str, value: Any, tenant: str = "default") -> None:
    """Lazy import and set setting."""
    from .models import BrainSetting
    BrainSetting.set(key, value, tenant)


def initialize_defaults(tenant: str = "default") -> int:
    """Lazy import and initialize defaults."""
    from .models import BrainSetting
    return BrainSetting.initialize_defaults(tenant)


# We keep symbols for internal use but avoid top-level model import
# that triggers AppRegistryNotReady during early app discovery.
__all__ = [
    "get",
    "set",
    "initialize_defaults",
]
