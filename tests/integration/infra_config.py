"""Centralized configuration for Integration Tests against Real Infrastructure.

VIBE Rule: Centralize Variables for Testing.
This file defines the canonical ports for local Docker services.
"""

# Service Ports (Localhost Mappings from Docker Compose)
# ---------------------------------------------------------------------------
# These ports match the actual docker-compose.yml port mappings for SomaBrain
PORTS = {
    "redis": 30100,       # somabrain_redis -> 6379
    "milvus": 30119,      # somabrain_milvus -> 19530
    "postgres": 30106,    # somabrain_postgres -> 5432
    "kafka": 30102,       # somabrain_kafka -> 9094
    "opa": 30104,         # somabrain_opa -> 8181
    "somafractalmemory": 10101,  # SFM API
    "somabrain": 30101,   # somabrain_app -> 9696
}

# Service URLs
# ---------------------------------------------------------------------------
URLS = {
    "opa": f"http://127.0.0.1:{PORTS['opa']}",
    "sfm": f"http://127.0.0.1:{PORTS['somafractalmemory']}",
    "milvus": f"127.0.0.1:{PORTS['milvus']}",
    "redis": f"redis://:somastack2024@127.0.0.1:{PORTS['redis']}/0",
    "postgres": f"postgresql://postgres:somastack2024@127.0.0.1:{PORTS['postgres']}/somabrain",
}

# Authentication
# ---------------------------------------------------------------------------
AUTH = {
    "sfm_token": "dev-token-somastack2024",
    "api_token": "dev-token-somastack2024",
}
