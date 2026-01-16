"""SomaBrain Configuration Module.

VIBE COMPLIANT: Provides Config class for backward compatibility.
The Config class wraps Django settings to provide a consistent interface
for the memory_client and other modules that expect a Config object.

This module exists to satisfy imports from modules that expect a
Config class rather than directly using Django settings.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Optional

from django.conf import settings


@dataclass
class Config:
    """Configuration container for SomaBrain components.

    This class wraps Django settings to provide a consistent interface
    for components like MemoryClient that expect a Config object.

    Attributes mirror Django settings with sensible defaults.
    """

    # Memory service configuration
    memory_http_endpoint: str = field(
        default_factory=lambda: getattr(
            settings,
            "SOMABRAIN_MEMORY_HTTP_ENDPOINT",
            os.environ.get("SOMABRAIN_MEMORY_HTTP_ENDPOINT", "http://localhost:10101"),
        )
    )
    memory_http_token: Optional[str] = field(
        default_factory=lambda: getattr(
            settings,
            "SOMABRAIN_MEMORY_HTTP_TOKEN",
            os.environ.get("SOMABRAIN_MEMORY_HTTP_TOKEN", None),
        )
    )

    # Namespace for memory scoping
    namespace: str = field(
        default_factory=lambda: getattr(
            settings,
            "SOMABRAIN_NAMESPACE",
            os.environ.get("SOMABRAIN_NAMESPACE", "somabrain:default"),
        )
    )

    # Database paths
    memory_db_path: str = field(
        default_factory=lambda: getattr(
            settings,
            "MEMORY_DB_PATH",
            os.environ.get("MEMORY_DB_PATH", "./data/memory.db"),
        )
    )

    # HTTP client tuning
    http_max_connections: int = field(
        default_factory=lambda: int(
            getattr(
                settings,
                "HTTP_MAX_CONNECTIONS",
                os.environ.get("HTTP_MAX_CONNECTIONS", 64),
            )
        )
    )
    http_keepalive_connections: int = field(
        default_factory=lambda: int(
            getattr(
                settings,
                "HTTP_KEEPALIVE_CONNECTIONS",
                os.environ.get("HTTP_KEEPALIVE_CONNECTIONS", 32),
            )
        )
    )
    http_retries: int = field(
        default_factory=lambda: int(
            getattr(settings, "HTTP_RETRIES", os.environ.get("HTTP_RETRIES", 1))
        )
    )

    # Debug flags
    debug_memory_client: bool = field(
        default_factory=lambda: str(
            getattr(
                settings,
                "DEBUG_MEMORY_CLIENT",
                os.environ.get("DEBUG_MEMORY_CLIENT", "false"),
            )
        ).lower()
        in ("1", "true", "yes")
    )

    @classmethod
    def from_settings(cls) -> "Config":
        """Create Config instance from Django settings."""
        return cls()

    def __getattr__(self, name: str) -> Any:
        """Fall back to Django settings for undefined attributes."""
        try:
            return getattr(settings, name.upper())
        except AttributeError:
            try:
                return getattr(settings, name)
            except AttributeError:
                raise AttributeError(
                    f"'{type(self).__name__}' has no attribute '{name}'"
                )


# Singleton instance for convenience
_config_instance: Optional[Config] = None


def get_config() -> Config:
    """Get or create the Config singleton instance."""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance


# For backward compatibility with direct imports
default_config = get_config
