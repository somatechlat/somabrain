import numpy as np

from somabrain.wm import WorkingMemory


def test_wm_admit_recall_novelty():
    wm = WorkingMemory(capacity=3, dim=16)
    v1 = np.random.randn(16).astype("float32")
    v2 = np.random.randn(16).astype("float32")
    wm.admit(v1, {"id": 1})
    wm.admit(v2, {"id": 2})
    res = wm.recall(v1, top_k=1)
    assert len(res) == 1
    assert res[0][1]["id"] in (1, 2)
    n = wm.novelty(v1)
    assert 0.0 <= n <= 1.0
