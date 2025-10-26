import time

from somabrain.services.segmentation_service import Segmenter, CPDSegmenter


def test_segmenter_leader_change_and_max_dwell():
    s = Segmenter(max_dwell_ms=50)
    tenant = "t1"
    # First observation initializes state
    assert s.observe("2025-01-01T00:00:00Z", "state", tenant) is None
    # Same leader within dwell -> no boundary
    assert s.observe("2025-01-01T00:00:00Z", "state", tenant) is None
    # Leader change -> boundary emitted with previous domain
    out = s.observe("2025-01-01T00:00:01Z", "agent", tenant)
    assert out is not None
    domain, ts, dwell, evidence = out
    assert domain == "state"
    assert evidence == "leader_change"
    # Wait to exceed dwell and observe same leader -> max_dwell boundary
    time.sleep(0.06)
    out2 = s.observe("2025-01-01T00:00:02Z", "agent", tenant)
    assert out2 is not None
    domain2, ts2, dwell2, evidence2 = out2
    assert domain2 == "agent"
    assert evidence2 == "max_dwell"


def test_cpd_segmenter_triggers_on_z_threshold():
    cpd = CPDSegmenter(max_dwell_ms=0, min_samples=5, z_threshold=2.0, min_gap_ms=0, min_std=0.01)
    tenant = "t2"
    domain = "state"
    base_ts = "2025-01-01T00:00:00Z"
    # Warmup with low variance around 0.1
    for _ in range(5):
        assert cpd.observe(base_ts, tenant, domain, 0.1) is None
    # Outlier spike
    out = cpd.observe(base_ts, tenant, domain, 0.5)
    assert out is not None
    d, ts, dwell, evidence = out
    assert d == domain
    assert evidence == "cpd"
