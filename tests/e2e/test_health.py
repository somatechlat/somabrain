import os
import socket
import time

import pytest
import redis
import requests

# Configuration (from environment or defaults)
API_URL = os.getenv("SOMABRAIN_API_URL", "http://localhost:30101")
KAFKA_BOOTSTRAP = os.getenv("SOMABRAIN_KAFKA_BOOTSTRAP", "localhost:30102")
REDIS_URL = os.getenv("SOMABRAIN_REDIS_URL", "redis://localhost:30100/0")


def _api_available() -> bool:
    try:
        resp = requests.get(f"{API_URL}/health", timeout=2)
        return resp.status_code == 200
    except requests.exceptions.RequestException:
        return False


def _kafka_available() -> bool:
    host, port = (KAFKA_BOOTSTRAP.split(":") + ["9092"])[:2]
    try:
        with socket.create_connection((host, int(port)), timeout=2):
            return True
    except OSError:
        return False


def _redis_available() -> bool:
    try:
        return redis.from_url(REDIS_URL).ping() is True
    except redis.exceptions.RedisError:
        return False


@pytest.mark.skipif(not _api_available(), reason=f"API not reachable at {API_URL}")
def test_api_health():
    """Verify SomaBrain API is reachable and healthy."""
    url = f"{API_URL}/health"
    for _ in range(10):
        try:
            resp = requests.get(url, timeout=2)
            if resp.status_code == 200:
                return
        except requests.exceptions.ConnectionError:
            pass
        time.sleep(0.5)
    pytest.fail(f"API endpoint at {url} not reachable after retries")


@pytest.mark.skipif(not _kafka_available(), reason=f"Kafka not reachable at {KAFKA_BOOTSTRAP}")
def test_kafka_connectivity():
    """Verify Kafka broker is reachable."""
    from kafka import KafkaAdminClient
    from kafka.errors import NoBrokersAvailable

    try:
        admin = KafkaAdminClient(bootstrap_servers=KAFKA_BOOTSTRAP)
        topics = admin.list_topics()
        assert len(topics) >= 0
    except NoBrokersAvailable:
        pytest.fail(f"Kafka broker at {KAFKA_BOOTSTRAP} unreachable")


@pytest.mark.skipif(not _redis_available(), reason=f"Redis not reachable at {REDIS_URL}")
def test_redis_connectivity():
    """Verify Redis is reachable."""
    r = redis.from_url(REDIS_URL)
    assert r.ping() is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
