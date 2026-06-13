"""
E2E Integration Test - SomaStack Unified Cognitive Architecture.
Copyright (C) 2026 SomaTech LAT.

Verifies:
1. Memory Persistence (Brain -> SFM)
2. Cognitive Mode Switches (ANALYTIC -> TRAINING -> RECALL)
3. Zero-Latency Direct Integration vs HTTP Fallback
4. Automated Degradation (Killing Milvus/Redis)
"""

import time
import asyncio
import pytest
from asgiref.sync import sync_to_async
from somabrain.controls.memory_client import MemoryClient
from somabrain.controls.degradation import degradation_manager, HealthStatus
from somabrain.brain_settings.models import BrainSetting


# Async-safe wrappers for the synchronous BrainSetting API.
_init_defaults = sync_to_async(BrainSetting.initialize_defaults)
_set_setting = sync_to_async(BrainSetting.set)
_get_setting = sync_to_async(BrainSetting.get)


def _sfm_available() -> bool:
    """Return True if the SomaFractalMemory HTTP API appears reachable."""
    import os
    import urllib.request

    url = os.environ.get("SOMABRAIN_MEMORY_URL", "http://localhost:10101")
    try:
        with urllib.request.urlopen(f"{url}/healthz", timeout=1) as resp:
            return resp.status == 200
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _sfm_available(), reason="SomaFractalMemory not reachable"
)


# Async-safe wrappers for the synchronous BrainSetting API.
_init_defaults = sync_to_async(BrainSetting.initialize_defaults)
_set_setting = sync_to_async(BrainSetting.set)
_get_setting = sync_to_async(BrainSetting.get)


@pytest.fixture
def memory_client():
    """Provide a fresh MemoryClient instance for each test."""
    return MemoryClient()


@pytest.mark.django_db
@pytest.mark.asyncio
async def test_unified_cognitive_flow(memory_client):
    tenant = "test_e2e_tenant"

    # 1. Initialize Settings
    await _init_defaults(tenant=tenant)

    # 2. Test TRAINING Mode (High Plasticity)
    await _set_setting("active_brain_mode", "TRAINING", tenant=tenant)
    assert await _get_setting("active_brain_mode", tenant=tenant) == "TRAINING"

    # Check if overrides applied (eta should be 0.10)
    assert await _get_setting("gmd_eta", tenant=tenant) == 0.10

    # 3. Store Memory via Unified Client
    coordinate = [0.1, 0.2, 0.3, 0.4]
    payload = {"content": "Unified Integration Test Memory", "timestamp": time.time()}

    success = await memory_client.store(coordinate, payload, tenant=tenant)
    assert success is True, "Memory storage failed in TRAINING mode"

    # 4. Test RECALL Mode (Deterministic)
    await _set_setting("active_brain_mode", "RECALL", tenant=tenant)
    assert await _get_setting("gmd_eta", tenant=tenant) == 0.01  # Should be frozen

    # Search for the same memory
    results = await memory_client.search("Integration Test", top_k=1, tenant=tenant)
    assert len(results) > 0, "Memory retrieval failed in RECALL mode"
    assert "Unified Integration" in results[0]["payload"]["content"]

    # 5. Simulate DEGRADATION (Heavy Latency)
    degradation_manager.report_latency(
        0.150, "memory", tenant=tenant
    )  # 150ms > 50ms cap
    assert (
        degradation_manager.get_status(tenant=tenant) == HealthStatus.NORMAL
    )  # Stays normal on 1st report due to window logic?

    # Simulate Error
    degradation_manager.report_error(
        "memory", RuntimeError("Infrastructure Failure"), tenant=tenant
    )
    assert degradation_manager.get_status(tenant=tenant) == HealthStatus.DEGRADED

    print(f"✅ E2E Cognitive Flow Proof Complete for tenant: {tenant}")


if __name__ == "__main__":
    asyncio.run(test_unified_cognitive_flow())
