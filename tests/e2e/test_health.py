import os
import time
import requests
import redis
import pytest
from kafka import KafkaAdminClient
from kafka.errors import NoBrokersAvailable

# Configuration (from environment or defaults)
API_URL = os.getenv("SOMABRAIN_API_URL", "http://localhost:30101")
KAFKA_BOOTSTRAP = os.getenv("SOMABRAIN_KAFKA_BOOTSTRAP", "localhost:30102")
REDIS_URL = os.getenv("SOMABRAIN_REDIS_URL", "redis://localhost:30100/0")

def test_api_health():
    """Verify SomaBrain API is reachable and healthy."""
    url = f"{API_URL}/health"
    print(f"Checking API health at {url}...")

    for _ in range(10):  # Retry loop
        try:
            resp = requests.get(url, timeout=2)
            if resp.status_code == 200:
                print("API Health: OK")
                return
        except requests.exceptions.ConnectionError:
            pass
        time.sleep(2)

    pytest.fail(f"API endpoints at {url} not reachable after retries")

def test_kafka_connectivity():
    """Verify Kafka broker is reachable."""
    print(f"Checking Kafka at {KAFKA_BOOTSTRAP}...")
    try:
        admin = KafkaAdminClient(bootstrap_servers=KAFKA_BOOTSTRAP)
        topics = admin.list_topics()
        print(f"Kafka Connected. Topics: {len(topics)}")
        assert len(topics) >= 0
    except NoBrokersAvailable:
        pytest.fail(f"Kafka broker at {KAFKA_BOOTSTRAP} unreachable")

def test_redis_connectivity():
    """Verify Redis is reachable."""
    print(f"Checking Redis at {REDIS_URL}...")
    try:
        r = redis.from_url(REDIS_URL)
        assert r.ping() is True
        print("Redis Ping: OK")
    except redis.exceptions.ConnectionError:
        pytest.fail(f"Redis at {REDIS_URL} unreachable")

if __name__ == "__main__":
    test_api_health()
    test_kafka_connectivity()
    test_redis_connectivity()
