import time
import os
import pytest

from somabrain.services.segmentation_service import Segmenter, CPDSegmenter, HazardSegmenter


def test_segmenter_dedupe_min_gap():
    seg = Segmenter(max_dwell_ms=0, min_gap_ms=200)
    t0 = int(time.time() * 1000)

    # First observation initializes state
    assert seg.observe(str(t0), "state", tenant="t1") is None

    # Immediate leader change should emit
    out = seg.observe(str(t0 + 10), "agent", tenant="t1")
    assert out is not None
    domain, ts, dwell_ms, evidence = out
    assert evidence == "leader_change"

    # Another rapid flip within min_gap is suppressed
    out2 = seg.observe(str(t0 + 50), "state", tenant="t1")
    assert out2 is None

    # After min_gap, emits again
    out3 = seg.observe(str(t0 + 250), "state", tenant="t1")
    assert out3 is not None


def test_cpd_min_gap_and_dwell():
    cpd = CPDSegmenter(max_dwell_ms=100, min_samples=3, z_threshold=1.0, min_gap_ms=200, min_std=0.01)
    t0 = int(time.time() * 1000)

    # Warmup
    for i in range(3):
        assert cpd.observe(str(t0 + i * 10), "t1", "state", 0.1) is None

    # Spike triggers CPD boundary
    out = cpd.observe(str(t0 + 40), "t1", "state", 2.0)
    assert out is not None
    domain, ts, dwell_ms, evidence = out
    assert evidence == "cpd"

    # Another spike within min_gap suppressed
    out2 = cpd.observe(str(t0 + 50), "t1", "state", 2.0)
    assert out2 is None

    # Dwell forces boundary after threshold
    out3 = cpd.observe(str(t0 + 300), "t1", "state", 0.1)
    assert out3 is not None
    assert out3[3] == "max_dwell"


def test_hazard_min_gap_and_states():
    hz = HazardSegmenter(max_dwell_ms=100, hazard_lambda=0.5, vol_sigma_mult=3.0, min_samples=3, min_gap_ms=200, min_std=0.01)
    t0 = int(time.time() * 1000)

    # Warmup on small noise
    for i in range(3):
        assert hz.observe(str(t0 + i * 10), "t1", "state", 0.05) is None

    # Large deviation likely triggers HMM boundary
    out = hz.observe(str(t0 + 40), "t1", "state", 1.0)
    if out is not None:
        assert out[3] in ("hmm", "max_dwell")

    # Gap within min_gap should not trigger
    out2 = hz.observe(str(t0 + 60), "t1", "state", 1.0)
    assert out2 is None

    # Dwell forces
    out3 = hz.observe(str(t0 + 300), "t1", "state", 0.05)
    assert out3 is not None
    assert out3[3] == "max_dwell"
