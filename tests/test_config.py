# SomaBrain Test Infrastructure Configuration
# This file centralizes all infrastructure endpoints used by tests
# to ensure consistency with actual running services.

import os
from urllib.parse import urlparse

from somabrain.infrastructure import (
    get_api_base_url,
    get_kafka_bootstrap,
    get_memory_http_endpoint,
    get_opa_url,
    get_postgres_dsn,
    get_redis_url,
    require,
)

# === Core Infrastructure Ports ===
# These should match ports.json and actual running services

# SomaBrain API Service
SOMABRAIN_API_URL = require(
    get_api_base_url() or os.getenv("SOMA_API_URL"),
    message="Set SOMABRAIN_API_URL (see .env) for test infrastructure.",
)
_api_parts = urlparse(SOMABRAIN_API_URL)
SOMABRAIN_HOST = _api_parts.hostname or os.getenv("SOMABRAIN_HOST", "127.0.0.1")
SOMABRAIN_PORT = _api_parts.port or int(os.getenv("SOMABRAIN_HOST_PORT", "9696"))

# SomaBrain Memory Service 
MEMORY_HTTP_ENDPOINT = require(
    get_memory_http_endpoint()
    or os.getenv("SOMABRAIN_MEMORY_HTTP_ENDPOINT")
    or os.getenv("MEMORY_SERVICE_URL"),
    message="Set SOMABRAIN_MEMORY_HTTP_ENDPOINT for test infrastructure.",
)
_memory_parts = urlparse(MEMORY_HTTP_ENDPOINT)
MEMORY_HOST = _memory_parts.hostname or os.getenv("SOMABRAIN_MEMORY_HOST", "127.0.0.1")
MEMORY_PORT = _memory_parts.port or int(os.getenv("SOMABRAIN_MEMORY_HTTP_PORT", "9595"))

# Redis Cache
REDIS_URL = require(
    get_redis_url()
    or os.getenv("SOMABRAIN_REDIS_URL")
    or os.getenv("REDIS_URL"),
    message="Set SOMABRAIN_REDIS_URL for test infrastructure.",
)
_redis_parts = urlparse(REDIS_URL)
REDIS_HOST = _redis_parts.hostname or os.getenv("SOMABRAIN_REDIS_HOST", "127.0.0.1")
REDIS_PORT = _redis_parts.port or int(os.getenv("SOMABRAIN_REDIS_PORT", "6379"))

# Kafka Message Broker
KAFKA_URL = require(
    get_kafka_bootstrap()
    or os.getenv("SOMABRAIN_KAFKA_URL")
    or os.getenv("KAFKA_BOOTSTRAP_SERVERS"),
    message="Set SOMABRAIN_KAFKA_URL for test infrastructure.",
)
_kafka_url = KAFKA_URL
if "://" not in _kafka_url:
    _kafka_url = f"kafka://{_kafka_url}"
_kafka_parts = urlparse(_kafka_url)
KAFKA_HOST = _kafka_parts.hostname or os.getenv("KAFKA_HOST", "127.0.0.1")
KAFKA_PORT = _kafka_parts.port or int(os.getenv("SOMABRAIN_KAFKA_PORT", "9092"))

# PostgreSQL Database  
POSTGRES_DSN = require(
    get_postgres_dsn() or os.getenv("SOMABRAIN_POSTGRES_DSN"),
    message="Set SOMABRAIN_POSTGRES_DSN for test infrastructure.",
)
_pg_parts = urlparse(POSTGRES_DSN)
POSTGRES_HOST = _pg_parts.hostname or os.getenv("POSTGRES_HOST", "127.0.0.1")
POSTGRES_PORT = _pg_parts.port or int(os.getenv("POSTGRES_PORT", "5432"))

# OPA Policy Engine
OPA_URL = require(
    get_opa_url()
    or os.getenv("SOMABRAIN_OPA_URL")
    or os.getenv("SOMA_OPA_URL"),
    message="Set SOMABRAIN_OPA_URL for test infrastructure.",
)
_opa_parts = urlparse(OPA_URL)
OPA_HOST = _opa_parts.hostname or os.getenv("OPA_HOST", "127.0.0.1")
OPA_PORT = _opa_parts.port or int(os.getenv("SOMABRAIN_OPA_PORT", "8181"))

# Prometheus Monitoring
PROMETHEUS_HOST = os.getenv("PROMETHEUS_HOST", "127.0.0.1")  
PROMETHEUS_PORT = int(os.getenv("PROMETHEUS_PORT", "9090"))
PROMETHEUS_URL = f"http://{PROMETHEUS_HOST}:{PROMETHEUS_PORT}"

# === Test Configuration ===
# Test-specific settings and flags

# Strict real mode - no mocks/stubs allowed
STRICT_REAL_MODE = os.getenv("SOMABRAIN_STRICT_REAL", "1").lower() in ("1", "true", "yes")

# Allow fakeredis only for development (never in CI)
ALLOW_FAKEREDIS = os.getenv("SOMABRAIN_ALLOW_FAKEREDIS", "0").lower() in ("1", "true", "yes")

# Force full stack usage
FORCE_FULL_STACK = os.getenv("SOMABRAIN_FORCE_FULL_STACK", "1").lower() in ("1", "true", "yes")

# Require memory service availability
REQUIRE_MEMORY = os.getenv("SOMABRAIN_REQUIRE_MEMORY", "1").lower() in ("1", "true", "yes")

# Test server URL (can override SOMABRAIN_API_URL for tests)
TEST_SERVER_URL = os.getenv("TEST_SERVER_URL", SOMABRAIN_API_URL)

# === Service Health Check URLs ===
HEALTH_URLS = {
    "somabrain": f"{SOMABRAIN_API_URL}/health",
    "memory": f"{MEMORY_HTTP_ENDPOINT}/health", 
    "redis": f"redis://{REDIS_HOST}:{REDIS_PORT}",
    "kafka": f"{KAFKA_HOST}:{KAFKA_PORT}",
    "postgres": POSTGRES_DSN,
    "opa": f"{OPA_URL}/health?plugins",
    "prometheus": f"{PROMETHEUS_URL}/-/healthy"
}

# === Test Headers and Authentication ===
DEFAULT_TEST_HEADERS = {
    "Content-Type": "application/json",
    "X-Model-Confidence": "8.5",
    "User-Agent": "SomaBrain-Test-Suite/1.0"
}

# Test tenant configuration  
DEFAULT_TENANT = os.getenv("SOMABRAIN_DEFAULT_TENANT", "sandbox")
TEST_TENANT_HEADERS = {"X-Tenant-ID": DEFAULT_TENANT}

# === Utility Functions ===
def get_service_url(service: str) -> str:
    """Get the full URL for a service by name."""
    urls = {
        "somabrain": SOMABRAIN_API_URL,
        "memory": MEMORY_HTTP_ENDPOINT, 
        "redis": REDIS_URL,
        "kafka": KAFKA_URL,
        "postgres": POSTGRES_DSN,
        "opa": OPA_URL,
        "prometheus": PROMETHEUS_URL
    }
    return urls.get(service, "")

def get_test_headers(tenant: str = None, session_id: str = None, **kwargs) -> dict:
    """Generate test headers with optional tenant and session ID."""
    headers = DEFAULT_TEST_HEADERS.copy()
    
    if tenant:
        headers["X-Tenant-ID"] = tenant
    elif DEFAULT_TENANT != "sandbox":
        headers["X-Tenant-ID"] = DEFAULT_TENANT
        
    if session_id:
        headers["X-Session-ID"] = session_id
        
    headers.update(kwargs)
    return headers

def is_service_available(service: str) -> bool:
    """Check if a service is available by attempting connection."""
    import socket
    
    if service == "redis":
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1.0)
            result = sock.connect_ex((REDIS_HOST, REDIS_PORT))
            sock.close()
            return result == 0
        except Exception:
            return False
            
    elif service in ("kafka", "opa", "postgres"):
        # Use appropriate connection logic for each service type
        if service == "kafka":
            host, port = KAFKA_HOST, KAFKA_PORT
        elif service == "opa": 
            host, port = OPA_HOST, OPA_PORT
        elif service == "postgres":
            host, port = POSTGRES_HOST, POSTGRES_PORT
            
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2.0)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except Exception:
            return False
            
    elif service in ("somabrain", "memory", "prometheus"):
        # HTTP-based services - try health check
        try:
            import requests
            url = HEALTH_URLS.get(service, "")
            if url:
                response = requests.get(url, timeout=2.0)
                return response.status_code == 200
        except Exception:
            return False
            
    return False

# === Export Configuration Summary ===
CONFIG_SUMMARY = {
    "somabrain_api": SOMABRAIN_API_URL,
    "memory_service": MEMORY_HTTP_ENDPOINT,
    "redis": REDIS_URL,
    "kafka": KAFKA_URL, 
    "postgres": POSTGRES_DSN,
    "opa": OPA_URL,
    "prometheus": PROMETHEUS_URL,
    "strict_real": STRICT_REAL_MODE,
    "allow_fakeredis": ALLOW_FAKEREDIS,
    "default_tenant": DEFAULT_TENANT
}

if __name__ == "__main__":
    print("=== SomaBrain Test Infrastructure Configuration ===")
    for service, url in CONFIG_SUMMARY.items():
        status = "✅ Available" if is_service_available(service.split("_")[0]) else "❌ Unavailable"
        print(f"{service:15}: {url} [{status}]")