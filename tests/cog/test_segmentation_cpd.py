from __future__ import annotations

from somabrain.services.segmentation_service import CPDSegmenter


def test_cpd_emits_on_shift():
    cpd = CPDSegmenter(max_dwell_ms=0, min_samples=5, z_threshold=3.0, min_gap_ms=0)
    tenant = "sandbox"
    domain = "state"
    # Warmup around mean ~0.0
    for i in range(5):
        assert cpd.observe(str(1000 + i * 10), tenant, domain, 0.05) is None
    # Moderate noise shouldn't trigger yet
    assert cpd.observe("1100", tenant, domain, 0.1) is None
    # Big change triggers boundary
    out = cpd.observe("1200", tenant, domain, 1.2)
    assert out is not None
    d, ts, dwell, ev = out
    assert d == domain
    assert ts == "1200"
    assert ev == "cpd"


def test_cpd_max_dwell_boundary():
    cpd = CPDSegmenter(max_dwell_ms=100, min_samples=2, z_threshold=10.0, min_gap_ms=0)
    tenant = "sandbox"
    domain = "agent"
    # First sample initializes state
    assert cpd.observe("1000", tenant, domain, 0.0) is None
    # No CPD, but dwell reaches threshold
    out = cpd.observe("1110", tenant, domain, 0.0)
    assert out is not None
    d, ts, dwell, ev = out
    assert d == domain
    assert ts == "1110"
    assert dwell == 110
    assert ev == "max_dwell"
