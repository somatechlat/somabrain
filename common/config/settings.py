"""Centralised configuration for SomaBrain and shared infra.

This module mirrors the pattern used by other services in the SomaStack.
It provides a single ``Settings`` class (pydantic ``BaseSettings``) that
loads values from ``.env.local`` or the environment.  All new code should
import ``Settings`` from here instead of calling ``os.getenv`` directly.

The implementation is deliberately permissive – existing code that still
reads environment variables will continue to work because the default values
fallback to the current variables.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from pydantic import BaseSettings, Field, PostgresDsn, RedisDsn


class Settings(BaseSettings):
    """Application‑wide settings.

    The fields correspond to the environment variables that SomaBrain already
    uses.  ``env_file`` points at the generated ``.env.local`` so developers
    can run the service locally without manually exporting each variable.
    """

    # Core infra -----------------------------------------------------------
    postgres_dsn: PostgresDsn = Field(
        default_factory=lambda: os.getenv(
            "SOMABRAIN_POSTGRES_DSN", "sqlite:///./data/somabrain.db"
        )
    )
    redis_url: RedisDsn = Field(
        default_factory=lambda: os.getenv(
            "SOMABRAIN_REDIS_URL", "redis://localhost:6379/0"
        )
    )
    kafka_bootstrap_servers: str = Field(
        default_factory=lambda: os.getenv(
            "SOMABRAIN_KAFKA_URL", "kafka://localhost:9092"
        )
    )

    # Auth / JWT -----------------------------------------------------------
    jwt_secret: Optional[str] = Field(default=os.getenv("SOMABRAIN_JWT_SECRET"))
    jwt_public_key_path: Optional[Path] = Field(
        default=os.getenv("SOMABRAIN_JWT_PUBLIC_KEY_PATH")
    )

    # Feature flags --------------------------------------------------------
    force_full_stack: bool = Field(
        default=os.getenv("SOMABRAIN_FORCE_FULL_STACK") == "1"
    )
    strict_real: bool = Field(
        default=os.getenv("SOMABRAIN_STRICT_REAL") == "1"
    )
    require_memory: bool = Field(
        default=os.getenv("SOMABRAIN_REQUIRE_MEMORY") == "1"
    )
    mode: str = Field(default=os.getenv("SOMABRAIN_MODE", "enterprise"))

    class Config:
        env_file = ".env.local"
        case_sensitive = False


# Export a singleton – mirrors the historic pattern used throughout the
# codebase (``settings = Settings()``).
settings = Settings()
