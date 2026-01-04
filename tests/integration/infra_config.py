"""Centralized configuration for Integration Tests against Real Infrastructure.

VIBE Rule: Centralize Variables for Testing.
This file defines the canonical ports for local Docker services.
"""

# Service Ports (Localhost Mappings from Docker Compose)
# ---------------------------------------------------------------------------
PORTS = {
    "redis": 20379,
    "milvus": 20530,
    "postgres": 20432,
    "kafka": 20092,
    "opa": 20181,
    "somafractalmemory": 10101,  # Local process
    "somabrain": 9696,
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
