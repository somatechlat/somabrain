"""Database helpers for SomaBrain.

Provides a lazily-initialized SQLAlchemy engine/session factory that defaults to
Postgres when `SOMABRAIN_POSTGRES_DSN` is defined, otherwise falls back to a
local SQLite database (useful for tests). The helpers centralise engine creation
so modules can share pools safely without reconfiguring per import.
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
    """Return the configured database URL.

    Preference order:
    1. SOMABRAIN_POSTGRES_DSN (official name)
    2. SOMABRAIN_DB_URL (generic override)
    3. sqlite:///./data/somabrain.db (local fallback for tests/dev)
    """

    url = None
    if shared_settings is not None:
        try:
            url = (
                str(getattr(shared_settings, "postgres_dsn", "") or "").strip() or None
            )
        except Exception:
            url = None
    if not url:
        url = os.getenv("SOMABRAIN_POSTGRES_DSN") or os.getenv("SOMABRAIN_DB_URL")
    if url:
        return url
    # Ensure data directory exists for SQLite fallback
    data_dir = pathlib.Path("./data")
    data_dir.mkdir(parents=True, exist_ok=True)
    return "sqlite:///" + str((data_dir / "somabrain.db").resolve())


def reset_engine(url: Optional[str] = None) -> None:
    """Reset the global engine/session factory (used in tests)."""

    global _ENGINE, _SESSION_FACTORY
    _ENGINE = None
    _SESSION_FACTORY = None
    if url:
        os.environ["SOMABRAIN_DB_URL"] = url


def get_engine(url: Optional[str] = None) -> Engine:
    """Return a shared SQLAlchemy engine (creating it on first use)."""

    global _ENGINE
    if url:
        os.environ["SOMABRAIN_DB_URL"] = url
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
