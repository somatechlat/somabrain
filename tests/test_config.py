# SomaBrain Test Infrastructure Configuration
# This file centralizes all infrastructure endpoints used by tests
# to ensure consistency with actual running services.

import os

# === Core Infrastructure Ports ===
# These should match ports.json and actual running services

# SomaBrain API Service
SOMABRAIN_HOST = os.getenv("SOMABRAIN_HOST", "127.0.0.1")
SOMABRAIN_PORT = int(os.getenv("SOMABRAIN_PORT", "9696"))
SOMABRAIN_API_URL = os.getenv("SOMA_API_URL", f"http://{SOMABRAIN_HOST}:{SOMABRAIN_PORT}")

# SomaBrain Memory Service 
MEMORY_HOST = os.getenv("SOMABRAIN_MEMORY_HOST", "127.0.0.1")
MEMORY_PORT = int(os.getenv("SOMABRAIN_MEMORY_PORT", "9596"))  # Updated from 9595 to match ports.json
MEMORY_HTTP_ENDPOINT = os.getenv("SOMABRAIN_MEMORY_HTTP_ENDPOINT", f"http://{MEMORY_HOST}:{MEMORY_PORT}")

# Redis Cache
REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")  
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))  # Updated from 55077 to match ports.json
REDIS_URL = os.getenv("SOMABRAIN_REDIS_URL", f"redis://{REDIS_HOST}:{REDIS_PORT}/0")

# Kafka Message Broker
KAFKA_HOST = os.getenv("KAFKA_HOST", "127.0.0.1")
KAFKA_PORT = int(os.getenv("KAFKA_PORT", "9092"))
KAFKA_URL = os.getenv("SOMABRAIN_KAFKA_URL", f"kafka://{KAFKA_HOST}:{KAFKA_PORT}")

# PostgreSQL Database  
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "127.0.0.1")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "15432"))  # Custom port from ports.json
POSTGRES_DSN = os.getenv("SOMABRAIN_POSTGRES_DSN", f"postgresql://soma:soma_pass@{POSTGRES_HOST}:{POSTGRES_PORT}/somabrain")

# OPA Policy Engine
OPA_HOST = os.getenv("OPA_HOST", "127.0.0.1")
OPA_PORT = int(os.getenv("OPA_PORT", "8181"))
OPA_URL = os.getenv("SOMABRAIN_OPA_URL", f"http://{OPA_HOST}:{OPA_PORT}")

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