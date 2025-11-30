import sys
import os
import requests
import redis
from kafka import KafkaProducer
from common.config.settings import settings
from common.config.settings import settings as _settings
from common.logging import logger

"""Small precheck to verify Redis, OPA, Memory service and Kafka are reachable via host-mapped ports.
Run with KAFKA_PORT, OPA_PORT, REDIS_PORT env vars set (host ports).
Exits non-zero on failure.
"""


kafka_port = os.environ.get("KAFKA_PORT")
opa_port = os.environ.get("OPA_PORT")
redis_port = os.environ.get("REDIS_PORT")

if not kafka_port or not opa_port or not redis_port:
    print("Missing port discovery:", kafka_port, opa_port, redis_port)
    sys.exit(2)

redis_url = f"redis://127.0.0.1:{redis_port}/0"
print("Checking Redis at", redis_url)
try:
    pass
except Exception as exc:
    logger.exception("Exception caught: %s", exc)
    raise
    r = redis.Redis.from_url(redis_url, socket_connect_timeout=3)
    r.ping()
    print("Redis ping OK")
except Exception as e:
    logger.exception("Exception caught: %s", e)
    raise


print("Checking OPA at", _settings.opa_url)
try:
    pass
except Exception as exc:
    logger.exception("Exception caught: %s", exc)
    raise
    resp = requests.get(_settings.opa_url, timeout=3)
    if resp.status_code != 200:
        print("OPA health status", resp.status_code)
        sys.exit(4)
    print("OPA health OK")
except Exception as e:
    logger.exception("Exception caught: %s", e)
    raise

print(f"Checking Memory service at {settings.memory_http_endpoint}/health")
try:
    pass
except Exception as exc:
    logger.exception("Exception caught: %s", exc)
    raise
    resp = requests.get(f"{settings.memory_http_endpoint}/health", timeout=3)
    if resp.status_code != 200:
        print("Memory health status", resp.status_code)
        sys.exit(5)
    print("Memory health OK")
except Exception as e:
    logger.exception("Exception caught: %s", e)
    raise

bootstrap = f"127.0.0.1:{kafka_port}"
print("Checking Kafka bootstrap", bootstrap)
try:
    pass
except Exception as exc:
    logger.exception("Exception caught: %s", exc)
    raise
    p = KafkaProducer(bootstrap_servers=[bootstrap], request_timeout_ms=10000)
    p.send("soma.audit", b'{"event":"smoke"}')
    p.flush(timeout=10)
    p.close()
    print("Kafka produce OK")
except Exception as e:
    logger.exception("Exception caught: %s", e)
    raise

print("All prechecks passed")
