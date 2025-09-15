import pytest

# Skip the test gracefully if the redis python package is not installed.
redis = pytest.importorskip("redis")


def test_redis_ping_localhost():
    """Simple integration test: connect to Redis on localhost:6379 and ping.

    This test is a smoke check for the dockerized Redis instance used in
    development. It will be skipped if the redis client library is not
    available in the test environment.
    """
    client = redis.Redis(host="127.0.0.1", port=6379, db=0, socket_connect_timeout=2)
    # ping() returns True on success; ensure we can connect
    assert client.ping() is True
