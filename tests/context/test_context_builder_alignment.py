import json
import math
import os
from typing import Iterable, List

import numpy as np

from somabrain.context.builder import ContextBuilder, RetrievalWeights, MemoryRecord


class _DummyMemory:
    def __init__(self, ids: List[str]):
        self._ids = ids

    def search_text(
        self, query_text: str, top_k: int, filters=None
    ):  # pragma: no cover - simple test shim
        res = []
        for i in range(min(top_k, len(self._ids))):
            rid = self._ids[i]
            res.append(
                {
                    "id": rid,
                    "score": 1.0,
                    "metadata": {"timestamp": 0.0, "graph_score": 0.0},
                    "embedding": (
                        np.ones(8) if i % 2 == 0 else np.ones(8) * 0.5
                    ).tolist(),
                }
            )
        return res


def _embed_fn(_: str) -> Iterable[float]:
    return [1.0] * 8


def _entropy_vec(alpha, beta, gamma, tau):
    vec = [max(1e-9, alpha), max(1e-9, beta), max(1e-9, gamma), max(1e-9, tau)]
    s = sum(vec)
    ps = [v / s for v in vec]
    return -sum(p * math.log(p) for p in ps)


def test_context_builder_entropy_cap_from_overrides(monkeypatch):
    monkeypatch.setenv(
        "SOMABRAIN_LEARNING_TENANTS_OVERRIDES",
        json.dumps({"public": {"entropy_cap": 1.0}}),
    )
    mem = _DummyMemory(
        ["a", "a", "b", "c"]
    )  # duplicates to exercise tau change but not required
    weights = RetrievalWeights(alpha=1.0, beta=1.0, gamma=1.0, tau=1.0)
    cb = ContextBuilder(embed_fn=_embed_fn, memory=mem, weights=weights)
    cb.set_tenant("public")
    bundle = cb.build("hello", top_k=4)
    assert bundle is not None
    H = _entropy_vec(
        cb.weights.alpha, cb.weights.beta, cb.weights.gamma, cb.weights.tau
    )
    assert H <= 1.0 + 1e-6
