"""Unit tests for MemoryService helper methods."""

from __future__ import annotations

import pytest

from somabrain.services.memory_service import MemoryService


class _StubBackend:
    def __init__(self, client):
        self._client = client

    def for_namespace(self, namespace: str):
        self.namespace = namespace
        return self._client


class _ClientWithScores:
    def __init__(self):
        self.recall_with_scores_called = False
        self.recall_called = False

    def recall_with_scores(self, query, top_k=3, universe=None):
        self.recall_with_scores_called = True
        return [
            {
                "payload": {"task": query, "universe": universe},
                "score": 0.99,
            }
        ]

    def recall(self, *args, **kwargs):  # pragma: no cover - should not run
        self.recall_called = True
        return []


class _ClientWithoutScores:
    def __init__(self):
        self.recall_called = False

    def recall(self, query, top_k=3, universe=None):
        self.recall_called = True
        return [
            {
                "payload": {"task": query, "universe": universe},
                "score": 0.42,
            }
        ]


class _AsyncClientWithScores:
    def __init__(self):
        self.arecall_with_scores_called = False

    async def arecall_with_scores(self, query, top_k=3, universe=None):
        self.arecall_with_scores_called = True
        return [
            {
                "payload": {"task": query, "universe": universe},
                "score": 0.88,
            }
        ]

    async def arecall(self, *args, **kwargs):  # pragma: no cover
        return []


def test_recall_with_scores_prefers_client_method() -> None:
    backend = _StubBackend(_ClientWithScores())
    svc = MemoryService(backend, "demo:tenant")

    hits = svc.recall_with_scores("alpha", top_k=2, universe="real")

    assert backend._client.recall_with_scores_called is True
    assert backend._client.recall_called is False
    assert hits and hits[0]["payload"]["task"] == "alpha"


def test_recall_with_scores_falls_back_to_recall_when_missing() -> None:
    backend = _StubBackend(_ClientWithoutScores())
    svc = MemoryService(backend, "demo:tenant")

    hits = svc.recall_with_scores("beta", top_k=1, universe="real")

    assert backend._client.recall_called is True
    assert hits and hits[0]["payload"]["task"] == "beta"


@pytest.mark.asyncio
async def test_arecall_with_scores_prefers_async_client_method() -> None:
    backend = _StubBackend(_AsyncClientWithScores())
    svc = MemoryService(backend, "demo:tenant")

    hits = await svc.arecall_with_scores("gamma", top_k=1, universe="real")

    assert backend._client.arecall_with_scores_called is True
    assert hits and hits[0]["payload"]["task"] == "gamma"
