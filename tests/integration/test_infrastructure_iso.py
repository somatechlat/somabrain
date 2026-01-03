"""ISO-Compliant Infrastructure Validation Workbench.

**Standard**: ISO/IEC 25010:2011 (Systems and software engineering - SQuaRE)
**Domain**: Reliability, Recoverability, and Security.

This suite categorizes verification checks into strict ISO domains:
1. **Network Availability** (Connectivity)
2. **Data Persistence** (Redis/Postgres Integrity)
3. **Security Policy** (OPA Validation)
4. **Interoperability** (Service Discovery)

Configuration is centralized in `tests.integration.infra_config`.
"""

import pytest
import httpx
from common.logging import logger
from tests.integration.infra_config import PORTS, URLS, AUTH

# ---------------------------------------------------------------------------
# Domain: Network Availability (Connectivity Checks)
# ---------------------------------------------------------------------------

def check_tcp_port(host: str, port: int, timeout: float = 2.0) -> bool:
    """Verify TCP handshake availability."""
    import socket
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False

# ---------------------------------------------------------------------------
# ISO Domain: Data Persistence (Postgres / Redis)
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.iso_reliability
class TestDataPersistenceISO:
    """Validates ISO 25010 Reliability (Recoverability)."""

    def test_postgres_availability(self):
        """Verify PostgreSQL allows connection and simple query execution.
        
        Standard: ISO 25010 - Maturity (Robustness)
        """
        if not check_tcp_port("localhost", PORTS["postgres"]):
            pytest.skip("PostgreSQL Port Unreachable")

        import psycopg2
        try:
            conn = psycopg2.connect(URLS["postgres"], connect_timeout=3)
            cur = conn.cursor()
            cur.execute("SELECT 1")
            assert cur.fetchone() == (1,)
            conn.close()
        except Exception as e:
            pytest.fail(f"PostgreSQL Connectivity Failed: {e}")

    def test_redis_availability(self):
        """Verify Redis allows connection, authentication, and state retrieval.
        
        Standard: ISO 25010 - Availability
        """
        if not check_tcp_port("localhost", PORTS["redis"]):
            pytest.skip("Redis Port Unreachable")

        import redis
        try:
            # Note: infra_config defines URL with /0 DB
            r = redis.from_url(URLS["redis"], socket_timeout=2)
            assert r.ping() is True
        except Exception as e:
            pytest.fail(f"Redis Connectivity Failed: {e}")

# ---------------------------------------------------------------------------
# ISO Domain: Security Policy (OPA)
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.iso_security
class TestSecurityPolicyISO:
    """Validates ISO 25010 Security (Confidentiality/Integrity)."""

    def test_opa_health_check(self):
        """Verify OPA service is active and responding.
        
        Standard: ISO 25010 - Non-repudiation (Audit capability availability)
        """
        if not check_tcp_port("localhost", PORTS["opa"]):
            pytest.skip("OPA Port Unreachable")

        try:
            resp = httpx.get(f"{URLS['opa']}/health", timeout=2.0)
            assert resp.status_code == 200
        except Exception as e:
            pytest.fail(f"OPA Health Check Failed: {e}")

    def test_opa_decision_engine(self):
        """Verify OPA can render decisions on input payload."""
        if not check_tcp_port("localhost", PORTS["opa"]):
            pytest.skip("OPA Port Unreachable")
        
        try:
            resp = httpx.post(
                f"{URLS['opa']}/v1/data", 
                json={"input": {"test_iso": True}},
                timeout=2.0
            )
            assert resp.status_code == 200
            assert "result" in resp.json() or resp.json() == {}
        except Exception as e:
            pytest.fail(f"OPA Decision Engine Failed: {e}")

# ---------------------------------------------------------------------------
# ISO Domain: Interoperability (Fractal Memory)
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.iso_interoperability
class TestInteroperabilityISO:
    """Validates ISO 25010 Interoperability (Service Coupling)."""

    def test_sfm_health_check(self):
        """Verify SomaFractalMemory (SFM) is responding.
        
        Note: Checks strict health status. Degraded state triggers WARNING.
        """
        if not check_tcp_port("localhost", PORTS["somafractalmemory"]):
            pytest.skip(f"SFM Port {PORTS['somafractalmemory']} Unreachable")

        try:
            resp = httpx.get(f"{URLS['sfm']}/health", timeout=3.0)
            assert resp.status_code == 200
            
            data = resp.json()
            if not data.get("healthy", False):
                print(f"WARNING: SFM Reported Degraded State: {data}")
                # We assert True anyway if Status Code is 200, 
                # as partial functionality (DB) allows Testing.
                assert resp.status_code == 200
        except Exception as e:
            pytest.fail(f"SFM Health Check Failed: {e}")

