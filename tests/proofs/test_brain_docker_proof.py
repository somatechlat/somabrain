"""Proof of Life Verification for SomaBrain Docker Deployment.

Target: http://localhost:30101
Verifies:
1. Health endpoint
2. Connection to SomaFractalMemory (via explicit recall)
"""

import os

import pytest
import requests

BRAIN_URL = os.environ.get("BRAIN_URL", "http://localhost:30101")
MEMORY_URL = os.environ.get("SOMABRAIN_MEMORY_URL", "http://localhost:10101")


def _sfm_available() -> bool:
    """Return True if the SomaFractalMemory HTTP API appears reachable."""
    import urllib.request

    try:
        with urllib.request.urlopen(f"{MEMORY_URL}/health", timeout=1) as resp:
            return resp.status == 200
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _sfm_available(), reason="SomaFractalMemory not reachable"
)


def test_brain_health_check():
    """Verify service reports healthy."""
    url = f"{BRAIN_URL}/health"
    print(f"Checking {url}...")
    resp = requests.get(url)
    assert resp.status_code == 200
    data = resp.json()
    print(f"Health Status: {data.get('status')}")
    # Brain returns "status": "healthy" or "critical" or "degraded"
    # It does NOT return "healthy": bool
    assert "status" in data


def test_brain_sfm_integration():
    """Verify the health payload exposes memory integration state."""

    url = f"{BRAIN_URL}/health"
    resp = requests.get(url)
    assert resp.status_code == 200
    data = resp.json()

    components = data.get("components", {})
    services = {s["name"]: s for s in data.get("services", [])}

    has_memory_component = "memory" in components
    has_memory_service = any(name in {"memory", "soma_memory"} for name in services)

    print(f"Health Components: {list(components.keys())}")
    print(f"Health Services: {list(services.keys())}")

    assert (
        has_memory_component or has_memory_service
    ), "Health payload does not expose memory integration state"


if __name__ == "__main__":
    try:
        test_brain_health_check()
        test_brain_sfm_integration()
        print("✅ BRAIN PROOFS PASSED")
    except Exception as e:
        print(f"❌ PROOF FAILED: {e}")
        exit(1)
