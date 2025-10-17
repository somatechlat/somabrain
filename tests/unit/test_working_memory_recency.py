import math

import numpy as np

from somabrain.wm import WorkingMemory


class _Recorder:
    def __init__(self) -> None:
        self.last_steps = None

    def score(self, query_vec, candidate_vec, *, recency_steps=None, cosine=None):
        self.last_steps = recency_steps
        # return bounded score to keep recall stable in assertions
        return float(recency_steps or 0.0)


def test_working_memory_recency_uses_time_scale() -> None:
    current = [0.0]

    def now_fn() -> float:
        return current[0]

    scorer = _Recorder()
    wm = WorkingMemory(
        capacity=4,
        dim=2,
        scorer=scorer,
        recency_time_scale=2.0,
        recency_max_steps=8.0,
        now_fn=now_fn,
    )

    vec = np.ones(2, dtype=np.float32)
    wm.admit(vec, {"id": 1})
    current[0] = 6.0

    wm.recall(vec, top_k=1)

    assert math.isclose(scorer.last_steps or 0.0, 3.0, rel_tol=1e-9)


def test_working_memory_recency_respects_cap() -> None:
    current = [0.0]

    def now_fn() -> float:
        return current[0]

    scorer = _Recorder()
    wm = WorkingMemory(
        capacity=4,
        dim=2,
        scorer=scorer,
        recency_time_scale=1.0,
        recency_max_steps=5.0,
        now_fn=now_fn,
    )

    vec = np.ones(2, dtype=np.float32)
    wm.admit(vec, {"id": 1})
    current[0] = 12.0

    wm.recall(vec, top_k=1)

    assert math.isclose(scorer.last_steps or 0.0, 5.0, rel_tol=1e-9)


def test_working_memory_density_penalizes_overlap() -> None:
    wm = WorkingMemory(capacity=3, dim=2, scorer=None)
    base = np.array([1.0, 0.0], dtype=np.float32)
    wm.admit(base, {"id": "unique"}, cleanup_overlap=0.1)
    wm.admit(base, {"id": "duplicate"}, cleanup_overlap=0.9)

    hits = wm.recall(base, top_k=2)

    assert hits[0][1]["id"] == "unique"
