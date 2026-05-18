"""Centralized configuration for Integration Tests against Real Infrastructure.

VIBE Rule: Centralize Variables for Testing.
This file defines the canonical ports for local Docker services.
"""

import os

# Service Ports (Localhost Mappings from Docker Compose)
# ---------------------------------------------------------------------------
# These ports match the actual docker-compose.yml port mappings for SomaBrain
PORTS = {
    "redis": 30100,  # somabrain_redis -> 6379
    "milvus": 30119,  # somabrain_milvus -> 19530
    "postgres": 30106,  # somabrain_postgres -> 5432
    "kafka": 30102,  # somabrain_kafka -> 9094
    "opa": 30104,  # somabrain_opa -> 8181
    "somafractalmemory": 10101,  # SFM API
    "somabrain": 30101,  # somabrain_app -> 30101
}

# Service URLs
# ---------------------------------------------------------------------------
_POSTGRES_USER = os.getenv("TEST_PG_USER", os.getenv("POSTGRES_USER", "somabrain"))
_POSTGRES_PASSWORD = os.getenv(
    "TEST_PG_PASSWORD",
    os.getenv("POSTGRES_PASSWORD", ""),
)
_POSTGRES_DB = os.getenv("TEST_PG_DB", os.getenv("POSTGRES_DB", "somabrain"))
if _POSTGRES_PASSWORD:
    _POSTGRES_AUTH = f"{_POSTGRES_USER}:{_POSTGRES_PASSWORD}@"
else:
    _POSTGRES_AUTH = f"{_POSTGRES_USER}@"

URLS = {
    "opa": f"http://127.0.0.1:{PORTS['opa']}",
    "sfm": f"http://127.0.0.1:{PORTS['somafractalmemory']}",
    "milvus": f"127.0.0.1:{PORTS['milvus']}",
    "redis": f"redis://127.0.0.1:{PORTS['redis']}/0",
    "postgres": f"postgresql://{_POSTGRES_AUTH}127.0.0.1:{PORTS['postgres']}/{_POSTGRES_DB}",
}

# Authentication
# ---------------------------------------------------------------------------
AUTH = {
    "sfm_token": os.getenv("SOMABRAIN_MEMORY_HTTP_TOKEN", ""),
    "api_token": os.getenv(
        "SOMABRAIN_API_TOKEN",
        os.getenv("SOMABRAIN_MEMORY_HTTP_TOKEN", ""),
    ),
}
