"""Module test_recall_quality."""

from __future__ import annotations

import time
from typing import List, Set

import httpx
import pytest

try:  # load .env for convenience
    from dotenv import load_dotenv

    load_dotenv(dotenv_path=".env", override=False)
except Exception:
    pass

from django.conf import settings
from tests.utils.metrics import precision_at_k, recall_at_k, ndcg_at_k


# Use centralized Settings for test configuration
MEM_URL = settings.SOMABRAIN_MEMORY_HTTP_ENDPOINT or "http://localhost:9595"
MEM_TOKEN = settings.SOMABRAIN_MEMORY_HTTP_TOKEN
API_URL = settings.SOMABRAIN_API_URL or "http://localhost:30101"


def _memory_available() -> bool:
    """Execute memory available."""

    try:
        headers = {"Authorization": f"Bearer {MEM_TOKEN}"} if MEM_TOKEN else {}
        url = MEM_URL.rstrip("/")
        try:
            r = httpx.get(f"{url}/health", timeout=2.0, headers=headers)
        except Exception:
            # Fallback to localhost if host.docker.internal is unreachable.
            r = httpx.get("http://localhost:9595/health", timeout=2.0, headers=headers)
        return r.status_code < 500
    except Exception:
        return False


def _api_available() -> bool:
    """Execute api available."""

    try:
        base = API_URL or "http://localhost:30101"
        r = httpx.get(f"{base.rstrip('/')}/health", timeout=2.0)
        if r.status_code < 500:
            return True
        r = httpx.get("http://localhost:30101/health", timeout=2.0)
        return r.status_code < 500
    except Exception:
        return False


@pytest.fixture(scope="session")
def http_client() -> httpx.Client:
    """Execute http client."""

    if not MEM_TOKEN:
        pytest.skip("SOMABRAIN_MEMORY_HTTP_TOKEN must be set for workbench tests")
    if not _memory_available():
        pytest.skip("Memory service not reachable for workbench tests")
    if not _api_available():
        pytest.skip("Somabrain API not reachable for workbench tests")
    base = API_URL
    try:
        httpx.get(f"{base.rstrip('/')}/health", timeout=1.0)
    except Exception:
        base = "http://localhost:30101"
    return httpx.Client(base_url=base, timeout=5.0)


def _remember(client: httpx.Client, tenant: str, text: str) -> None:
    """Execute remember.

    Args:
        client: The client.
        tenant: The tenant.
        text: The text.
    """

    payload = {"payload": {"task": text, "content": text, "memory_type": "episodic"}}
    r = client.post("/memory/remember", headers={"X-Tenant-ID": tenant}, json=payload)
    assert r.status_code == 200, r.text


def _recall_texts(client: httpx.Client, tenant: str, query: str, k: int) -> List[str]:
    """Execute recall texts.

    Args:
        client: The client.
        tenant: The tenant.
        query: The query.
        k: The k.
    """

    r = client.post(
        "/memory/recall",
        headers={"X-Tenant-ID": tenant},
        json={"query": query, "top_k": k},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    results = body.get("results") or body.get("memory") or []
    texts = [str(item.get("content") or item.get("text") or "") for item in results]
    return texts


def test_recall_quality_basic(http_client: httpx.Client) -> None:
    """Execute test recall quality basic.

    Args:
        http_client: The http_client.
    """

    tenant = "workbench-quality"
    corpus = {
        "alpha solar storage": {
            "query": "alpha solar storage",
            "relevant": {"alpha solar storage"},
        },
        "beta wind turbine": {
            "query": "beta wind turbine",
            "relevant": {"beta wind turbine"},
        },
        "gamma battery study": {
            "query": "gamma battery study",
            "relevant": {"gamma battery study"},
        },
    }
    # Ingest
    for text in corpus:
        _remember(http_client, tenant, text)
    time.sleep(0.3)

    # Evaluate
    precisions = []
    recalls = []
    ndcgs = []
    for text, meta in corpus.items():
        retrieved = _recall_texts(http_client, tenant, meta["query"], k=5)
        relevant: Set[str] = meta["relevant"]
        precisions.append(precision_at_k(relevant, retrieved, k=5))
        recalls.append(recall_at_k(relevant, retrieved, k=5))
        # Build binary relevance vector aligned with retrieved list
        rel_scores = [1 if item in relevant else 0 for item in retrieved[:5]]
        ndcgs.append(ndcg_at_k(rel_scores, k=5))

    assert all(p >= 0.2 for p in precisions), f"Precision too low: {precisions}"
    assert all(r >= 0.8 for r in recalls), f"Recall too low: {recalls}"
    assert all(n >= 0.2 for n in ndcgs), f"nDCG too low: {ndcgs}"


def test_multi_tenant_isolation(http_client: httpx.Client) -> None:
    """Execute test multi tenant isolation.

    Args:
        http_client: The http_client.
    """

    tenant_a = "workbench-tenant-a"
    tenant_b = "workbench-tenant-b"
    text_a = "alpha unique payload"
    text_b = "beta distinct payload"
    _remember(http_client, tenant_a, text_a)
    _remember(http_client, tenant_b, text_b)
    time.sleep(0.2)

    res_a = _recall_texts(http_client, tenant_a, "alpha", k=5)
    res_b = _recall_texts(http_client, tenant_b, "beta", k=5)

    assert any(text_a in t for t in res_a), "Tenant A recall missing its payload"
    assert all(text_a not in t for t in res_b), "Tenant B leaked Tenant A payload"
    assert any(text_b in t for t in res_b), "Tenant B recall missing its payload"


def test_recall_includes_degraded_flag(http_client: httpx.Client) -> None:
    """Execute test recall includes degraded flag.

    Args:
        http_client: The http_client.
    """

    tenant = "workbench-degraded"
    r = http_client.post(
        "/memory/recall",
        headers={"X-Tenant-ID": tenant},
        json={"query": "noop", "top_k": 1},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "degraded" in body, "recall response missing degraded flag"
    assert isinstance(body.get("degraded"), (bool, type(None)))
