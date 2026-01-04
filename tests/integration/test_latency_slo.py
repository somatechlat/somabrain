"""Module test_latency_slo."""

from __future__ import annotations

import time

import httpx
import pytest

try:
    from dotenv import load_dotenv

    load_dotenv(".env", override=False)
except Exception:
    pass

from django.conf import settings

# Use centralized Settings for test configuration
API_URL = settings.SOMABRAIN_API_URL or "http://localhost:9696"
MEM_TOKEN = settings.SOMABRAIN_MEMORY_HTTP_TOKEN
TENANT = "workbench-slo"


def _api_available(url: str) -> bool:
    """Execute api available.

    Args:
        url: The url.
    """

    base = url.rstrip("/") or "http://localhost:9696"
    try:
        r = httpx.get(f"{base}/health", timeout=2.0)
        return r.status_code < 500
    except Exception:
        try:
            r = httpx.get("http://localhost:9696/health", timeout=2.0)
            return r.status_code < 500
        except Exception:
            return False


def _api_client() -> httpx.Client:
    """Execute api client."""

    base = API_URL or "http://localhost:9696"
    if not _api_available(base):
        raise RuntimeError("API unavailable")
    if not base.rstrip("/"):
        base = "http://localhost:9696"
    return httpx.Client(base_url=base.rstrip("/"), timeout=5.0)


@pytest.mark.integration
def test_latency_slo_basic() -> None:
    """Execute test latency slo basic."""

    if not MEM_TOKEN:
        pytest.skip("SOMABRAIN_MEMORY_HTTP_TOKEN required for latency SLO test")
    if not _api_available(API_URL):
        pytest.skip("Somabrain API not reachable for latency SLO test")

    try:
        client = _api_client()
    except RuntimeError:
        pytest.skip("Somabrain API not reachable for latency SLO test")
    headers = {"X-Tenant-ID": TENANT}
    remember_lat = []
    recall_lat = []

    # Warm-up to avoid cold-start skew
    for i in range(3):
        client.post(
            "/memory/remember",
            headers=headers,
            json={"payload": {"task": f"warm-{i}", "content": f"warm-{i}"}},
        )
    time.sleep(0.3)

    for i in range(5):
        payload = {
            "payload": {
                "task": f"slo-{i}",
                "content": f"slo-{i}",
                "memory_type": "episodic",
            }
        }
        t0 = time.time()
        r = client.post("/memory/remember", headers=headers, json=payload)
        assert r.status_code == 200, r.text
        remember_lat.append((time.time() - t0) * 1000)

    time.sleep(0.3)

    for i in range(5):
        t0 = time.time()
        r = client.post(
            "/memory/recall", headers=headers, json={"query": f"slo-{i}", "top_k": 1}
        )
        assert r.status_code == 200, r.text
        recall_lat.append((time.time() - t0) * 1000)

    # Use a simple percentile to avoid small-sample quantile sensitivity.
    def p95(values):
        """Execute p95.

        Args:
            values: The values.
        """

        if not values:
            return 0.0
        vs = sorted(values)
        idx = int(0.95 * (len(vs) - 1))
        return vs[idx]

    p95_remember = p95(remember_lat)
    p95_recall = p95(recall_lat)

    assert p95_remember < 600, f"p95 remember too high: {p95_remember:.1f} ms"
    assert p95_recall < 800, f"p95 recall too high: {p95_recall:.1f} ms"
