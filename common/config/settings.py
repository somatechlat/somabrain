"""Centralized configuration for SomaBrain and shared infra.

This module has been refactored into a modular package structure:
- common/config/settings/__init__.py - Main Settings class
- common/config/settings/base.py - Base utilities and helpers
- common/config/settings/infra.py - Infrastructure settings (Redis, Kafka, Postgres, Milvus)
- common/config/settings/memory.py - Memory settings (HTTP, weighting, WM, retrieval)
- common/config/settings/learning.py - Learning settings (adaptation, tau, neuromodulators)
- common/config/settings/auth.py - Authentication settings (JWT, OPA, provenance)
- common/config/settings/oak.py - Oak (ROAMDP) settings

All imports continue to work via this re-export module:
    from common.config.settings import settings

Configuration precedence (highest to lowest):
1. Environment variables
2. .env file
3. config.yaml
"""

# Re-export everything from the modular package for backward compatibility
from common.config.settings import (
    Settings,
    settings,
)

# Also re-export base utilities for any code that imports them directly
from common.config.settings.base import (
    _bool_env,
    _float_env,
    _int_env,
    _str_env,
    _yaml_get,
)

__all__ = [
    "Settings",
    "settings",
    "_bool_env",
    "_float_env",
    "_int_env",
    "_str_env",
    "_yaml_get",
]
