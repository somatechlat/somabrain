import math

import numpy as np

from somabrain.context import ContextBuilder, RetrievalWeights
from somabrain.runtime.working_memory import WorkingMemoryBuffer


class DummyMemstore:
    def __init__(self, results):
        self._results = results

    def search(self, embedding, top_k=5):
        return self._results[:top_k]


def constant_embed(text: str):
    rng = np.random.default_rng(abs(hash(text)) % (2**32))
    return rng.normal(size=4)


def test_context_builder_weights_sum_to_one(monkeypatch):
    working = WorkingMemoryBuffer()
    mem_results = [
        {
            "id": "a",
            "score": 0.9,
            "metadata": {"text": "A", "graph_score": 0.5, "timestamp": 0},
            "embedding": [0.2, 0.1, 0.3, 0.4],
        },
        {
            "id": "b",
            "score": 0.8,
            "metadata": {"text": "B", "graph_score": 0.1, "timestamp": 0},
            "embedding": [0.05, 0.2, 0.1, 0.1],
        },
    ]
    builder = ContextBuilder(
        embed_fn=constant_embed,
        memstore=DummyMemstore(mem_results),
        weights=RetrievalWeights(alpha=1.0, beta=0.2, gamma=0.1, tau=0.5),
        working_memory=working,
    )
    bundle = builder.build("hello", top_k=2, session_id="sess")
    assert len(bundle.weights) == 2
    assert math.isclose(sum(bundle.weights), 1.0, rel_tol=1e-6)
    assert bundle.working_memory_snapshot  # recorded item present
    assert "Context:" in bundle.prompt
    assert len(bundle.residual_vector) == 4
