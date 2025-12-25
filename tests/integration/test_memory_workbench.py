import time
from typing import List, Set

import httpx
import pytest

from django.conf import settings
from tests.utils.metrics import precision_at_k, recall_at_k, ndcg_at_k

# Use centralized Settings for test configuration
MEM_URL = settings.SOMABRAIN_MEMORY_HTTP_ENDPOINT or "http://localhost:9595"
MEM_TOKEN = settings.SOMABRAIN_MEMORY_HTTP_TOKEN


def _remember(client: httpx.Client, tenant: str, text: str) -> None:
    payload = {"payload": {"task": text, "content": text, "memory_type": "episodic"}}
    r = client.post("/memory/remember", headers={"X-Tenant-ID": tenant}, json=payload)
    assert r.status_code == 200, r.text


def _recall_texts(client: httpx.Client, tenant: str, query: str, k: int) -> List[str]:
    r = client.post(
        "/memory/recall",
        headers={"X-Tenant-ID": tenant},
        json={"query": query, "top_k": k},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    results = body.get("results") or body.get("memory") or []
    return [str(item.get("content") or item.get("text") or "") for item in results]


@pytest.mark.parametrize(
    "tenant, corpus",
    [
        (
            "workbench-basic",
            {
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
            },
        ),
    ],
)
def test_memory_workbench(http_client: httpx.Client, tenant, corpus) -> None:
    client = http_client
    for text in corpus:
        _remember(client, tenant, text)
    time.sleep(0.3)
    precisions: List[float] = []
    recalls: List[float] = []
    ndcgs: List[float] = []
    for text, meta in corpus.items():
        retrieved = _recall_texts(client, tenant, meta["query"], k=5)
        relevant: Set[str] = meta["relevant"]
        precisions.append(precision_at_k(relevant, retrieved, k=5))
        recalls.append(recall_at_k(relevant, retrieved, k=5))
        ndcgs.append(
            ndcg_at_k([1 if item in relevant else 0 for item in retrieved[:5]], k=5)
        )
    assert all(p >= 0.2 for p in precisions), f"Precision too low: {precisions}"
    assert all(r >= 0.8 for r in recalls), f"Recall too low: {recalls}"
    assert all(n >= 0.2 for n in ndcgs), f"nDCG too low: {ndcgs}"
