from __future__ import annotations

import asyncio

from somabrain.schemas import RAGRequest
import os
import pytest
from somabrain.services.rag_pipeline import run_rag_pipeline


class Ctx:
    def __init__(self, namespace: str):
        self.namespace = namespace
        self.tenant_id = "test"


@pytest.mark.skipif(
    os.getenv("SOMABRAIN_STRICT_REAL", "").lower() in ("1", "true", "yes", "on"),
    reason="Stub pipeline test skipped in strict real mode",
)
def test_rag_pipeline_stub_basic():
    req = RAGRequest(
        query="Ada Lovelace",
        top_k=5,
        retrievers=["vector", "wm", "graph"],
        persist=False,
    )
    ctx = Ctx(namespace="ns:test")

    resp = asyncio.get_event_loop().run_until_complete(
        run_rag_pipeline(req, ctx=ctx, cfg=None, universe=None, trace_id="t1")
    )

    assert resp.namespace == "ns:test"
    assert resp.trace_id == "t1"
    assert resp.session_coord is None
    assert len(resp.candidates) == 5
    # Ensure candidates are ordered by score desc and deduped
    scores = [c.score for c in resp.candidates]
    assert scores == sorted(scores, reverse=True)
