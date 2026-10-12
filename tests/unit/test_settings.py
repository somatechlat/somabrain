"""Test settings: real infra DSN forced over the Vault-assembled in-network one.

django_core.configure_vault_secrets() assembles SOMABRAIN_POSTGRES_DSN from
Vault using in-network hostnames (somabrain_standalone_postgres) that do not
resolve from the host test runner. This module loads production settings then
overrides DATABASES with the host-reachable test DSN from TEST_PG_*.
"""
import os
import urllib.parse as _up

# Topology must exist before settings import (Rule 91: no defaults).
os.environ.setdefault("ALLOWED_HOSTS", "localhost,127.0.0.1,testserver")
os.environ.setdefault("SOMABRAIN_NAMESPACE", "test-ns")
os.environ.setdefault("SOMABRAIN_HOST", "127.0.0.1")
os.environ.setdefault("SOMABRAIN_PORT", "30101")
os.environ.setdefault("SOMABRAIN_DEFAULT_TENANT", "default")
os.environ.setdefault("REQUIRE_EXTERNAL_BACKENDS", "false")
os.environ.setdefault("ENABLE_LEARNING_STATE_PERSISTENCE", "false")
os.environ.setdefault("SOMABRAIN_MEMORY_HTTP_TOKEN", "test-only-token")
os.environ.setdefault("SOMA_API_TOKEN", "test-sfm-token")

# Load production settings first.
from somabrain.settings import *  # noqa: F401,F403

# Force host-reachable DSN over the Vault-assembled one.
_dsn = os.environ.get("TEST_PG_DSN", "")
if _dsn.startswith("postgresql://") or _dsn.startswith("postgres://"):
    _u = _up.urlparse(_dsn)
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "HOST": _u.hostname or "127.0.0.1",
            "PORT": str(_u.port or 5432),
            "USER": _u.username or "",
            "PASSWORD": _u.password or "",
            "NAME": (_u.path or "/somabrain").lstrip("/"),
            "ATOMIC_REQUESTS": False,
            "AUTOCOMMIT": True,
            "CONN_MAX_AGE": 0,
            "CONN_HEALTH_CHECKS": False,
            "OPTIONS": {},
            "TEST": {"NAME": "test_somabrain", "MIRROR": None},
            "MIRROR": None,
        }
    }
