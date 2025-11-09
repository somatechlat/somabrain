from __future__ import annotations

from types import SimpleNamespace

import pytest

from somabrain.context.builder import ContextBuilder, MemoryRecord, RetrievalWeights
from somabrain.context.planner import ContextPlanner


def _dummy_embed(_: str):
    return [1.0, 0.0]


class _DummyMemory:
    def search(self, embedding, top_k=5):
        return []


def test_tau_configuration_overrides(monkeypatch) -> None:
    monkeypatch.setenv("SOMABRAIN_RECALL_TAU_INCREMENT_UP", "0.2")
    monkeypatch.setenv("SOMABRAIN_RECALL_TAU_INCREMENT_DOWN", "0.1")
    monkeypatch.setenv("SOMABRAIN_RECALL_TAU_MAX", "1.5")
    builder = ContextBuilder(_dummy_embed, memory=_DummyMemory())
    builder._weights = RetrievalWeights(alpha=1.0, beta=0.0, gamma=0.0, tau=0.6)
    memories = [
        MemoryRecord(
            id="dup",
            score=1.0,
            metadata={"timestamp": 0.0, "graph_score": 0.0},
            embedding=[0.5, 0.0],
        ),
        MemoryRecord(
            id="dup",
            score=0.8,
            metadata={"timestamp": 0.0, "graph_score": 0.0},
            embedding=[0.4, 0.0],
        ),
    ]
    builder._compute_weights([1.0, 0.0], memories)
    assert builder._weights.tau == pytest.approx(0.6)


def test_planner_penalty_scales(monkeypatch) -> None:
    monkeypatch.setenv("SOMABRAIN_PLANNER_LENGTH_PENALTY_SCALE", "2048")
    monkeypatch.setenv("SOMABRAIN_PLANNER_MEMORY_PENALTY_SCALE", "5")
    planner = ContextPlanner()
    assert planner._length_penalty_scale == pytest.approx(2048.0)
    assert planner._memory_penalty_scale == pytest.approx(5.0)
    bundle = SimpleNamespace(
        prompt="short prompt",
        query="q",
        weights=[0.4, 0.6],
        memories=[
            SimpleNamespace(metadata={"text": "a"}, id="a"),
            SimpleNamespace(metadata={"text": "b"}, id="b"),
        ],
    )
    score = planner._score(bundle, bundle.prompt)
    assert isinstance(score, float)
