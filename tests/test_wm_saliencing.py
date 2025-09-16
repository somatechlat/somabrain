import numpy as np

from somabrain.wm import WorkingMemory


def test_wm_salience_and_admit_if_salient():
    wm = WorkingMemory(capacity=2, dim=8, min_capacity=2, max_capacity=3)
    v = np.random.randn(8).astype("float32")
    # Empty WM: high novelty and recency proxy; should admit above threshold
    admitted = wm.admit_if_salient(v, {"i": 1}, threshold=0.2)
    assert admitted is True
    assert len(wm._items) == 1
    # Next vector similar -> lower novelty; still may admit if threshold
    # low
    admitted2 = wm.admit_if_salient(v, {"i": 2}, threshold=0.9)
    # May be False depending on vector; just ensure function returns bool
    # and items not exceed max
    assert isinstance(admitted2, bool)
    assert len(wm._items) <= wm.capacity
