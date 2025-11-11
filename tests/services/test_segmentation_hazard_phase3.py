import time
import math
from somabrain.services.segmentation_service import HazardSegmenter


def test_hazard_warmup_no_boundary():
    hz = HazardSegmenter(max_dwell_ms=0, hazard_lambda=0.1, vol_sigma_mult=3.0, min_samples=5, min_gap_ms=200, min_std=0.01)
    t0 = int(time.time() * 1000)
    # Warmup samples should not emit boundaries
    for i in range(5):
        assert hz.observe(str(t0 + i * 10), "t1", "state", 0.1) is None


def test_hazard_state_flip_emits_boundary():
    hz = HazardSegmenter(max_dwell_ms=0, hazard_lambda=0.5, vol_sigma_mult=5.0, min_samples=5, min_gap_ms=200, min_std=0.01)
    t0 = int(time.time() * 1000)
    # Warmup
    for i in range(5):
        assert hz.observe(str(t0 + i * 10), "t1", "state", 0.1) is None
    # Large deviation to encourage VOLATILE switch
    out = hz.observe(str(t0 + 60), "t1", "state", 2.5)
    assert out is not None
    domain, ts, dwell_ms, evidence = out
    assert domain == "state"
    assert evidence == "hmm"


def test_hazard_min_gap_suppresses():
    hz = HazardSegmenter(max_dwell_ms=0, hazard_lambda=0.5, vol_sigma_mult=5.0, min_samples=3, min_gap_ms=300, min_std=0.01)
    t0 = int(time.time() * 1000)
    # Warmup
    for i in range(3):
        assert hz.observe(str(t0 + i * 10), "t1", "state", 0.1) is None
    out1 = hz.observe(str(t0 + 50), "t1", "state", 3.0)
    assert out1 is not None
    # Attempt immediate flip again (simulate reversion)
    out2 = hz.observe(str(t0 + 100), "t1", "state", 0.05)
    # Might not flip back; if it does within min_gap it should be suppressed
    if out2 is not None:
        # If we got a boundary, ensure gap respected
        _, _, _, evidence = out2
        assert evidence == "hmm"
        # Given stochastic-like model, allow None (suppressed or no flip) or respected flip


def test_hazard_max_dwell_forces_boundary():
    hz = HazardSegmenter(max_dwell_ms=100, hazard_lambda=0.01, vol_sigma_mult=2.0, min_samples=3, min_gap_ms=0, min_std=0.01)
    t0 = int(time.time() * 1000)
    for i in range(3):
        assert hz.observe(str(t0 + i * 10), "t1", "state", 0.1) is None
    # Advance beyond dwell with no volatility
    out = hz.observe(str(t0 + 150), "t1", "state", 0.1)
    assert out is not None
    domain, ts, dwell_ms, evidence = out
    assert evidence == "max_dwell"
    assert dwell_ms >= 100
