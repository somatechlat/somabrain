"""Standalone test bootstrap.

These tests are supposed to exercise the standalone settings profile, but the
repo-level test bootstrap defaults Django to ``somabrain.settings``. Override
the settings module and database DSN here before ``django.setup()`` runs so the
standalone suite uses the correct app set and Postgres endpoint.
"""

from __future__ import annotations

import os

os.environ["DJANGO_SETTINGS_MODULE"] = "somabrain.settings.standalone"

_pg_user = os.environ.get("TEST_PG_USER", os.environ.get("POSTGRES_USER", "somabrain"))
_pg_password = os.environ.get(
    "TEST_PG_PASSWORD",
    os.environ.get("POSTGRES_PASSWORD", "somabrain"),
)
_pg_host = os.environ.get("TEST_PG_HOST", "localhost")
_pg_port = os.environ.get("TEST_PG_PORT", "30106")
_pg_db = os.environ.get("TEST_PG_DB", os.environ.get("POSTGRES_DB", "somabrain"))

_pg_dsn = f"postgresql://{_pg_user}:{_pg_password}@{_pg_host}:{_pg_port}/{_pg_db}"

os.environ["POSTGRES_PASSWORD"] = _pg_password
os.environ["TEST_PG_PASSWORD"] = _pg_password
os.environ["TEST_PG_DSN"] = _pg_dsn
os.environ["DATABASE_URL"] = _pg_dsn
os.environ["SOMABRAIN_POSTGRES_DSN"] = _pg_dsn
