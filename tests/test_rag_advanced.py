from __future__ import annotations

import asyncio
import types

import pytest

from somabrain.schemas import RAGRequest
from somabrain.services.rag_pipeline import run_rag_pipeline


class _Ctx:
    def __init__(self, namespace: str = "testns", tenant_id: str = "tenant"):
        self.namespace = namespace
        self.tenant_id = tenant_id


@pytest.fixture(autouse=True)
def _setup_runtime(tmp_path):
    # Configure a local runtime with in-memory backends
    from somabrain import runtime as _rt
    from somabrain.config import get_config
    from somabrain.memory_pool import MultiTenantMemory
    from somabrain.embeddings import make_embedder

    cfg = get_config()
    _rt.mt_memory = MultiTenantMemory(cfg)
    _rt.embedder = make_embedder(cfg)
    try:
        # Ensure no quantum for default tests (so auto -> mmr)
        _rt.quantum = None
    except Exception:
        pass
    yield


def _remember(key: str, payload: dict, namespace: str = "testns"):
    from somabrain import runtime as _rt
    from somabrain.services.memory_service import MemoryService

    memsvc = MemoryService(_rt.mt_memory, namespace)
    return memsvc.remember(key, payload)


def _coord_for_key(key: str, namespace: str = "testns"):
    from somabrain import runtime as _rt
    from somabrain.services.memory_service import MemoryService

    memsvc = MemoryService(_rt.mt_memory, namespace)
    return memsvc.coord_for_key(key)


@pytest.mark.asyncio
async def test_exact_key_mode_pinned_top():
    _remember("alpha123", {"task": "Alpha doc", "memory_type": "episodic"})
    # Sanity: ensure payloads_for_coords can retrieve stored payload
    from somabrain import runtime as _rt
    from somabrain.services.memory_service import MemoryService
    memsvc = MemoryService(_rt.mt_memory, "testns")
    coord = memsvc.coord_for_key("alpha123")
    payloads = memsvc.payloads_for_coords([coord])
    assert payloads, "Stored payload not retrievable by coordinate"
    ctx = _Ctx()
    req = RAGRequest(query="some other text", mode="key", key="alpha123", top_k=3, retrievers=["vector"]) 
    resp = await run_rag_pipeline(req, ctx=ctx, universe=None, trace_id="t1")
    assert resp.candidates, "No candidates returned"
    top = resp.candidates[0]
    assert top.retriever == "exact"
    assert isinstance(top.payload, dict) and (top.payload.get("task") == "Alpha doc")


@pytest.mark.asyncio
async def test_auto_coord_mode():
    _remember("beta777", {"task": "Beta doc", "memory_type": "episodic"})
    coord = _coord_for_key("beta777")
    coord_str = ",".join(str(float(c)) for c in coord[:3])
    # Sanity check
    from somabrain import runtime as _rt
    from somabrain.services.memory_service import MemoryService
    memsvc = MemoryService(_rt.mt_memory, "testns")
    payloads = memsvc.payloads_for_coords([coord])
    assert payloads, "Stored payload not retrievable by coordinate"
    ctx = _Ctx()
    req = RAGRequest(query="ignored", mode="auto", coord=coord_str, top_k=3, retrievers=["vector"]) 
    resp = await run_rag_pipeline(req, ctx=ctx, universe=None, trace_id="t2")
    assert resp.candidates, "No candidates returned"
    assert resp.candidates[0].retriever == "exact"


@pytest.mark.asyncio
async def test_auto_key_heuristic_single_token():
    _remember("gamma999", {"task": "Gamma doc", "memory_type": "episodic"})
    ctx = _Ctx()
    # Using the key as the query; heuristic should treat as key (no spaces, len>=6)
    req = RAGRequest(query="gamma999", top_k=3, retrievers=["vector"]) 
    resp = await run_rag_pipeline(req, ctx=ctx, universe=None, trace_id="t3")
    assert resp.candidates, "No candidates returned"
    assert resp.candidates[0].retriever == "exact"


@pytest.mark.asyncio
async def test_reranker_auto_selection_metric_present():
    _remember("delta888", {"task": "Delta doc", "memory_type": "episodic"})
    ctx = _Ctx()
    req = RAGRequest(query="delta888", top_k=3, retrievers=["vector"])  # default rerank -> auto
    resp = await run_rag_pipeline(req, ctx=ctx, universe=None, trace_id="t4")
    assert isinstance(resp.metrics, dict)
    assert resp.metrics.get("reranker_used") in ("hrr", "mmr", "cosine")
