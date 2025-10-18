from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pytest

import somabrain.runtime as runtime
from somabrain.schemas import RAGRequest
from somabrain.services.rag_pipeline import run_rag_pipeline


@dataclass
class _Ctx:
    namespace: str
    tenant_id: str = "test"


class _SimpleEmbedder:
    def embed(self, text: str) -> np.ndarray:
        # Deterministic embedding derived from character codes
        vec = np.zeros(8, dtype=np.float32)
        for idx, ch in enumerate(text.encode("utf-8")):
            vec[idx % 8] += float(ch)
        norm = np.linalg.norm(vec) or 1.0
        return vec / norm


class _RecallHit:
    def __init__(self, payload: dict):
        self.payload = payload


class _TestMemoryClient:
    def __init__(self, embedder: _SimpleEmbedder, docs: Iterable[str]):
        self._embedder = embedder
        self._docs = []
        for text in docs:
            payload = {"task": text, "memory_type": "episodic", "importance": 1}
            vector = self._embedder.embed(text)
            self._docs.append((vector, payload))

    def recall(self, query: str, top_k: int = 3, universe: str | None = None):
        qv = self._embedder.embed(query)
        ranked = []
        for vector, payload in self._docs:
            score = float(np.dot(qv, vector))
            ranked.append((score, payload))
        ranked.sort(key=lambda item: item[0], reverse=True)
        return [_RecallHit(payload) for score, payload in ranked[: max(1, int(top_k))]]


class _TestMultiTenantMemory:
    def __init__(self, client: _TestMemoryClient):
        self._client = client

    def for_namespace(self, namespace: str):  # pragma: no cover - simple passthrough
        return self._client


@pytest.fixture
def vector_runtime(monkeypatch):
    embedder = _SimpleEmbedder()
    docs = (
        "solar microgrid design",
        "battery storage safety checklist",
        "hydrogen fuel cell operations manual",
    )
    client = _TestMemoryClient(embedder, docs)
    mt_memory = _TestMultiTenantMemory(client)

    original_embedder = getattr(runtime, "embedder", None)
    original_mt_memory = getattr(runtime, "mt_memory", None)
    original_mt_wm = getattr(runtime, "mt_wm", None)
    original_mc_wm = getattr(runtime, "mc_wm", None)

    runtime.embedder = embedder
    runtime.mt_memory = mt_memory
    runtime.mt_wm = None
    runtime.mc_wm = None

    try:
        yield docs, embedder
    finally:
        if original_embedder is None and hasattr(runtime, "embedder"):
            delattr(runtime, "embedder")
        else:
            runtime.embedder = original_embedder
        if original_mt_memory is None and hasattr(runtime, "mt_memory"):
            delattr(runtime, "mt_memory")
        else:
            runtime.mt_memory = original_mt_memory
        runtime.mt_wm = original_mt_wm
        runtime.mc_wm = original_mc_wm


def test_rag_pipeline_vector_retriever(vector_runtime):
    docs, embedder = vector_runtime
    req = RAGRequest(
        query="microgrid battery operations",
        top_k=3,
        retrievers=["vector"],
        persist=False,
    )
    ctx = _Ctx(namespace="ns:test")

    resp = asyncio.run(run_rag_pipeline(req, ctx=ctx, cfg=None, universe=None, trace_id="trace-1"))

    assert resp.namespace == "ns:test"
    assert resp.trace_id == "trace-1"
    assert resp.session_coord is None
    assert 1 <= len(resp.candidates) <= len(docs)

    ranked = sorted(
        ((float(np.dot(embedder.embed(req.query), embedder.embed(doc))), doc) for doc in docs),
        reverse=True,
    )
    returned = [cand.payload.get("task") for cand in resp.candidates]
    assert returned == [doc for _, doc in ranked[: len(resp.candidates)]]
