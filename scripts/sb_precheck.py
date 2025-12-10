"""Small precheck to verify Redis, OPA, Memory service and Kafka are reachable via host-mapped ports.
Run with KAFKA_PORT, OPA_PORT, REDIS_PORT env vars set (host ports).
Exits non-zero on failure.
"""

import sys
import requests
import redis
from kafka import KafkaProducer
from common.config.settings import settings

# Use centralized Settings for port configuration
kafka_port = settings.kafka_port
opa_port = settings.opa_port
redis_port = settings.redis_port

if not kafka_port or not opa_port or not redis_port:
    print("Missing port discovery:", kafka_port, opa_port, redis_port)
    sys.exit(2)

redis_url = f"redis://127.0.0.1:{redis_port}/0"
print("Checking Redis at", redis_url)
try:
    r = redis.Redis.from_url(redis_url, socket_connect_timeout=3)
    r.ping()
    print("Redis ping OK")
except Exception as e:
    print("Redis check failed:", e)
    sys.exit(3)

from common.config.settings import settings as _settings

print("Checking OPA at", _settings.opa_url)
try:
    resp = requests.get(_settings.opa_url, timeout=3)
    if resp.status_code != 200:
        print("OPA health status", resp.status_code)
        sys.exit(4)
    print("OPA health OK")
except Exception as e:
    print("OPA check failed:", e)
    sys.exit(4)

print(f"Checking Memory service at {settings.memory_http_endpoint}/health")
try:
    resp = requests.get(f"{settings.memory_http_endpoint}/health", timeout=3)
    if resp.status_code != 200:
        print("Memory health status", resp.status_code)
        sys.exit(5)
    print("Memory health OK")
except Exception as e:
    print("Memory check failed:", e)
    sys.exit(5)

bootstrap = f"127.0.0.1:{kafka_port}"
print("Checking Kafka bootstrap", bootstrap)
try:
    p = KafkaProducer(bootstrap_servers=[bootstrap], request_timeout_ms=10000)
    p.send("soma.audit", b'{"event":"smoke"}')
    p.flush(timeout=10)
    p.close()
    print("Kafka produce OK")
except Exception as e:
    print("Kafka check failed:", e)
    sys.exit(6)

print("All prechecks passed")
