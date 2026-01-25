"""Integration tests against REAL infrastructure.

**Feature: production-hardening**
**Validates: Requirements 4.5, 5.1, 5.2, 5.3, 6.4, 10.3**

These tests run against REAL Redis, Kafka, Postgres, and OPA services.
They verify connectivity and basic operations against live infrastructure.

Required environment variables (or use defaults):
- SOMABRAIN_REDIS_URL: Redis connection URL
- SOMABRAIN_KAFKA_URL: Kafka broker URL
- SOMABRAIN_POSTGRES_DSN: PostgreSQL connection string
- SOMABRAIN_OPA_URL: OPA service URL
"""

from __future__ import annotations

import pytest
import httpx

from common.logging import logger


# ---------------------------------------------------------------------------
# Infrastructure availability checks
# ---------------------------------------------------------------------------


def _redis_available() -> bool:
    """Check if Redis is reachable on SomaBrain cluster."""
    try:
        import redis
        import os

        # Default to AAAS port 63979, allow override
        host = os.environ.get("SOMA_REDIS_HOST", "localhost")
        port = int(os.environ.get("SOMA_REDIS_PORT", "63979"))

        r = redis.Redis(host=host, port=port, socket_timeout=2)
        r.ping()
        return True
    except Exception:
        return False


def _kafka_available() -> bool:
    """Check if Kafka is reachable on SomaBrain cluster."""
    try:
        from kafka import KafkaAdminClient
        import os

        host = os.environ.get("SOMA_KAFKA_HOST", "localhost")
        port = int(os.environ.get("SOMA_KAFKA_PORT", "63992")) # Standard Kafka Port

        admin = KafkaAdminClient(
            bootstrap_servers=f"{host}:{port}",
            request_timeout_ms=2000,
        )
        admin.close()
        return True
    except Exception:
        return False


def _postgres_available() -> bool:
    """Check if PostgreSQL is reachable on SomaBrain cluster."""
    try:
        import psycopg2
        import os

        host = os.environ.get("SOMA_DB_HOST", "localhost")
        port = int(os.environ.get("SOMA_DB_PORT", "63932"))
        user = os.environ.get("SOMA_DB_USER", "soma")
        password = os.environ.get("SOMA_DB_PASSWORD", "soma")
        dbname = os.environ.get("SOMA_DB_NAME", "somabrain")

        conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            dbname=dbname,
            connect_timeout=3,
        )
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        conn.close()
        return True
    except Exception as exc:
        logger.warning("PostgreSQL not reachable: %s", exc)
        return False


def _opa_available() -> bool:
    """Check if OPA is reachable on SomaBrain cluster."""
    try:
        import os
        host = os.environ.get("SOMA_OPA_HOST", "localhost")
        port = int(os.environ.get("SOMA_OPA_PORT", "63999")) # Assumption for OPA? No, Agent used one.
        # Agent used SA01_OPA_URL. Let's use env var or skip if not sure.
        # But for valid verification, we need OPA.
        # Checking Agent env config (Step 1234): AAAS_ENV didn't list OPA explicitly?
        # Step 1210: "Missing required environment variable: SA01_OPA_URL".
        # I'll default to localhost:8181 (OPA default) or read URL.

        opa_url = os.environ.get("SOMA_OPA_URL", "http://localhost:8181")

        with httpx.Client(timeout=2.0) as client:
            resp = client.get(f"{opa_url}/health")
            if resp.status_code == 200:
                return True
        return False
    except Exception as exc:
        logger.warning("OPA not reachable: %s", exc)
        return False


# ---------------------------------------------------------------------------
# Redis Integration Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestRedisIntegration:
    """Integration tests against REAL Redis.

    **Validates: Requirements 4.5, 10.3**
    """

    def test_redis_ping(self) -> None:
        """Verify Redis responds to PING on SomaBrain cluster (port 30100)."""
        if not _redis_available():
            pytest.skip("Redis not reachable; skipping integration test")

        import redis

        r = redis.Redis(host="localhost", port=30100, socket_timeout=2)
        result = r.ping()
        assert result is True, "Redis PING should return True"

    def test_redis_set_get(self) -> None:
        """Verify Redis SET/GET operations work on SomaBrain cluster (port 30100)."""
        if not _redis_available():
            pytest.skip("Redis not reachable; skipping integration test")

        import redis

        r = redis.Redis(host="localhost", port=30100, socket_timeout=2)
        test_key = "somabrain:test:integration"
        test_value = "test_value_12345"

        # SET
        r.set(test_key, test_value, ex=60)  # 60 second expiry

        # GET
        result = r.get(test_key)
        assert result is not None, "GET should return a value"
        assert result.decode("utf-8") == test_value, "GET should return SET value"

        # Cleanup
        r.delete(test_key)

    def test_redis_hash_operations(self) -> None:
        """Verify Redis HASH operations for state persistence on SomaBrain cluster (port 30100)."""
        if not _redis_available():
            pytest.skip("Redis not reachable; skipping integration test")

        import redis

        r = redis.Redis(host="localhost", port=30100, socket_timeout=2)
        hash_key = "somabrain:test:adaptation_state"

        # HSET multiple fields
        r.hset(
            hash_key,
            mapping={
                "alpha": "0.5",
                "beta": "0.3",
                "tau": "0.1",
            },
        )

        # HGETALL
        result = r.hgetall(hash_key)
        assert len(result) == 3, "HGETALL should return 3 fields"
        assert result[b"alpha"] == b"0.5"
        assert result[b"beta"] == b"0.3"
        assert result[b"tau"] == b"0.1"

        # Cleanup
        r.delete(hash_key)


# ---------------------------------------------------------------------------
# Kafka Integration Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestKafkaIntegration:
    """Integration tests against REAL Kafka.

    **Validates: Requirements 5.2**
    """

    def test_kafka_list_topics(self) -> None:
        """Verify Kafka broker responds to metadata requests on SomaBrain cluster (port 30102)."""
        if not _kafka_available():
            pytest.skip("Kafka not reachable; skipping integration test")

        from kafka import KafkaAdminClient

        admin = KafkaAdminClient(
            bootstrap_servers="localhost:20092",
            request_timeout_ms=10000,
        )
        topics = admin.list_topics()
        assert isinstance(topics, list), "list_topics should return a list"
        admin.close()

    def test_kafka_cluster_metadata(self) -> None:
        """Verify Kafka cluster metadata is accessible on SomaBrain cluster (port 30102)."""
        if not _kafka_available():
            pytest.skip("Kafka not reachable; skipping integration test")

        from kafka import KafkaAdminClient

        admin = KafkaAdminClient(
            bootstrap_servers="localhost:20092",
            request_timeout_ms=10000,
        )
        # Get cluster metadata
        metadata = admin.describe_cluster()
        assert metadata is not None, "Cluster metadata should not be None"
        admin.close()


# ---------------------------------------------------------------------------
# PostgreSQL Integration Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestPostgresIntegration:
    """Integration tests against REAL PostgreSQL.

    **Validates: Requirements 5.3**
    """

    def test_postgres_select_one(self) -> None:
        """Verify PostgreSQL responds to SELECT 1 on SomaBrain cluster (port 30106)."""
        if not _postgres_available():
            pytest.skip("PostgreSQL not reachable; skipping integration test")

        import psycopg2

        conn = psycopg2.connect(
            host="localhost",
            port=20432,
            user="soma",
            password="soma_pass",
            dbname="somabrain",
            connect_timeout=5,
        )
        cur = conn.cursor()
        cur.execute("SELECT 1")
        result = cur.fetchone()
        assert result == (1,), "SELECT 1 should return (1,)"
        cur.close()
        conn.close()

    def test_postgres_version(self) -> None:
        """Verify PostgreSQL version is accessible on SomaBrain cluster (port 30106)."""
        if not _postgres_available():
            pytest.skip("PostgreSQL not reachable; skipping integration test")

        import psycopg2

        conn = psycopg2.connect(
            host="localhost",
            port=20432,
            user="soma",
            password="soma_pass",
            dbname="somabrain",
            connect_timeout=5,
        )
        cur = conn.cursor()
        cur.execute("SELECT version()")
        result = cur.fetchone()
        assert result is not None, "version() should return a result"
        assert "PostgreSQL" in result[0], "Version should contain 'PostgreSQL'"
        cur.close()
        conn.close()


# ---------------------------------------------------------------------------
# OPA Integration Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestOPAIntegration:
    """Integration tests against REAL OPA.

    **Validates: Requirements 6.4**
    """

    def test_opa_health(self) -> None:
        """Verify OPA health endpoint responds on SomaBrain cluster (port 30104)."""
        if not _opa_available():
            pytest.skip("OPA not reachable; skipping integration test")

        with httpx.Client(timeout=5.0) as client:
            resp = client.get("http://localhost:30104/health")
            # OPA health returns empty JSON {}
            assert resp.status_code == 200

    def test_opa_policy_query(self) -> None:
        """Verify OPA can evaluate a simple policy query on SomaBrain cluster (port 30104)."""
        if not _opa_available():
            pytest.skip("OPA not reachable; skipping integration test")

        with httpx.Client(timeout=5.0) as client:
            # Query a simple data path (may return empty if no policies loaded)
            resp = client.post(
                "http://localhost:30104/v1/data",
                json={"input": {"test": True}},
            )
            # OPA should respond with 200 even if no matching policy
            assert resp.status_code == 200, f"OPA query failed: {resp.status_code}"
            result = resp.json()
            assert (
                "result" in result or result == {}
            ), "OPA should return result key or empty"
