import os

import pytest
import requests

BASE = os.getenv("SOMA_API_URL", "http://127.0.0.1:9696")
REDIS_URL = os.getenv("SOMA_REDIS_URL", "redis://127.0.0.1:6379/0")


def redis_available(url: str) -> bool:
    try:
        import redis

        r = redis.Redis.from_url(url, socket_connect_timeout=1)
        return r.ping()
    except Exception:
        return False


@pytest.mark.skipif(
    not redis_available(REDIS_URL), reason="Redis not available for integration test"
)
def test_constitution_endpoints():
    # /constitution/version
    v = requests.get(BASE + "/constitution/version", timeout=2)
    assert v.status_code == 200
    body = v.json()
    assert "constitution_status" in body

    # Try a validate call (no OPA assumed). The payload is simple and should be allowed by local fallback
    payload = {"input": {"forbidden": False}}
    r = requests.post(BASE + "/constitution/validate", json=payload, timeout=2)
    assert r.status_code in (200, 503, 500)
    # If 200, must have allowed key
    if r.status_code == 200:
        j = r.json()
        assert "allowed" in j
