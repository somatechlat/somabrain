from __future__ import annotations

def test_hazard_segmenter_boundary():
    from somabrain.services.segmentation_service import HazardSegmenter

    hz = HazardSegmenter(
        max_dwell_ms=0,
        hazard_lambda=0.2,
        vol_sigma_mult=3.0,
        min_samples=5,
        min_gap_ms=0,
        min_std=0.01,
    )
    # Warmup stable values
    ts = 1_700_000_000_000
    for i in range(5):
        assert hz.observe(str(ts + i * 1000), "public", "state", 0.2) is None
    # Large deviation should flip to VOLATILE and emit a boundary
    out = hz.observe(str(ts + 6000), "public", "state", 1.2)
    assert out is not None
    domain, boundary_ts, dwell_ms, evidence = out
    assert domain == "state"
    assert evidence in ("hmm", "max_dwell")


def test_hazard_segmenter_min_gap():
    from somabrain.services.segmentation_service import HazardSegmenter

    hz = HazardSegmenter(
        max_dwell_ms=0,
        hazard_lambda=0.5,
        vol_sigma_mult=3.0,
        min_samples=3,
        min_gap_ms=4_000,
        min_std=0.01,
    )
    base = 1_700_000_100_000
    for i in range(3):
        assert hz.observe(str(base + i * 1000), "public", "agent", 0.1) is None
    # First big deviation triggers boundary
    first = hz.observe(str(base + 5000), "public", "agent", 1.0)
    assert first is not None
    # A subsequent deviation within min_gap should not trigger another boundary
    second = hz.observe(str(base + 8000), "public", "agent", 1.1)
    assert second is None
