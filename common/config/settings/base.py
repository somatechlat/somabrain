"""Base configuration utilities and helpers for SomaBrain settings.

This module provides the foundational utilities used by all settings modules:
- Environment variable parsing helpers with comment stripping
- YAML configuration loading
- Pydantic BaseSettings setup
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

# Load config.yaml as the base configuration source
_CONFIG_YAML: Dict[str, Any] = {}
try:
    import yaml

    _config_path = Path(__file__).parent.parent.parent.parent / "config.yaml"
    if _config_path.exists():
        with open(_config_path, "r") as f:
            _CONFIG_YAML = yaml.safe_load(f) or {}
except Exception:
    pass  # yaml not available or config.yaml not found

# Ensure the canonical .env file is loaded into os.environ
_ENV_PATH = Path(__file__).resolve().parents[3] / ".env"
if _ENV_PATH.exists():
    for line in _ENV_PATH.read_text(encoding="utf-8").splitlines():
        if not line or line.lstrip().startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def _yaml_get(key: str, default: Any = None) -> Any:
    """Get a value from config.yaml with fallback to default."""
    return _CONFIG_YAML.get(key, default)


# Pydantic setup
BaseSettings: Any
Field: Any
try:
    import pydantic_settings as _ps
    from pydantic_settings import SettingsConfigDict
    from pydantic import Field as _Field

    BaseSettings = _ps.BaseSettings
    Field = _Field
except Exception:
    from pydantic import BaseSettings as _BS, Field as _Field

    BaseSettings = _BS
    Field = _Field

    class SettingsConfigDict(dict):
        pass


_TRUE_VALUES = {"1", "true", "yes", "on"}


def _int_env(name: str, default: int | None = None) -> int | None:
    """Parse an integer environment variable safely.

    Strips any trailing # comment before conversion.
    """
    if default is None:
        raw = os.getenv(name)
        if raw is None:
            return None
        raw = raw.split("#", 1)[0].strip()
        try:
            return int(raw)
        except Exception:
            return None
    raw = os.getenv(name, str(default))
    raw = raw.split("#", 1)[0].strip()
    try:
        return int(raw)
    except Exception:
        return default


def _bool_env(name: str, default: bool) -> bool:
    """Parse a boolean environment variable safely.

    Supports typical truthy strings and strips comments.
    """
    raw = os.getenv(name)
    if raw is None:
        return default
    raw = raw.split("#", 1)[0].strip()
    try:
        return raw.lower() in _TRUE_VALUES
    except Exception:
        return default


def _float_env(name: str, default: float) -> float:
    """Parse a float environment variable safely, stripping comments."""
    raw = os.getenv(name, str(default))
    raw = raw.split("#", 1)[0].strip()
    try:
        return float(raw)
    except Exception:
        return default


def _str_env(name: str, default: str | None = None) -> str | None:
    """Return a string environment variable, stripping inline comments."""
    raw = os.getenv(name)
    if raw is None:
        return default
    raw = raw.split("#", 1)[0].strip()
    return raw if raw != "" else default
