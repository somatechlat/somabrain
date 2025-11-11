"""Database helpers for SomaBrain.

Provides a lazily-initialized SQLAlchemy engine/session factory that requires a
Postgres DSN (`SOMABRAIN_POSTGRES_DSN`). Strict mode removes the previous SQLite
alternative; attempts to start without a Postgres URL now raise immediately. This
prevents silent divergence between dev/test and production storage behaviour.
"""

from __future__ import annotations

import json
import os
import pathlib
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker


try:
    from common.config.settings import settings as shared_settings
except Exception:  # pragma: no cover - optional dependency during migration
    shared_settings = None  # type: ignore

Base = declarative_base()
_ENGINE: Optional[Engine] = None
_SESSION_FACTORY: Optional[sessionmaker] = None


def get_default_db_url() -> str:
    """Return the configured Postgres database URL or raise.

    Strict mode: SQLite alternative removed. The URL must be provided via
    `SOMABRAIN_POSTGRES_DSN` or settings.postgres_dsn. Empty / sqlite schemes
    trigger a RuntimeError to fail fast.
    """
    url: Optional[str] = None
    if shared_settings is not None:
        try:
            raw = str(getattr(shared_settings, "postgres_dsn", "") or "").strip()
            url = raw or None
        except Exception:
            url = None
    if not url:
        url = (os.getenv("SOMABRAIN_POSTGRES_DSN") or "").strip() or None
    if not url:
        raise RuntimeError(
            "storage.db: SOMABRAIN_POSTGRES_DSN not set (Postgres required)"
        )
    if url.startswith("sqlite:"):
        raise RuntimeError("storage.db: SQLite DSN forbidden in strict mode")
    return url


def reset_engine(url: Optional[str] = None) -> None:
    """Reset the global engine/session factory (used in tests)."""

    global _ENGINE, _SESSION_FACTORY
    _ENGINE = None
    _SESSION_FACTORY = None


def get_engine(url: Optional[str] = None) -> Engine:
    """Return a shared SQLAlchemy engine (creating it on first use)."""

    global _ENGINE
    if _ENGINE is None:
        db_url = url or get_default_db_url()
        # Configure JSON serializer/deserializer for consistent behaviour.
        _ENGINE = create_engine(
            db_url,
            future=True,
            json_serializer=lambda obj: json.dumps(obj, sort_keys=True),
            json_deserializer=json.loads,
        )
    return _ENGINE


def get_session_factory(url: Optional[str] = None) -> sessionmaker:
    """Return a shared session factory bound to the global engine."""

    global _SESSION_FACTORY
    if _SESSION_FACTORY is None or url is not None:
        engine = get_engine(url)
        _SESSION_FACTORY = sessionmaker(
            bind=engine, autoflush=False, expire_on_commit=False, future=True
        )
    return _SESSION_FACTORY


__all__ = [
    "Base",
    "get_engine",
    "get_session_factory",
    "get_default_db_url",
    "reset_engine",
]
