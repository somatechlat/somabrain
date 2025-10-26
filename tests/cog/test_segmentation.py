from __future__ import annotations

import time

from somabrain.services.segmentation_service import Segmenter


def test_segmenter_leader_change():
    s = Segmenter()
    # First observation initializes state
    assert s.observe("1000", "state") is None
    # Leader changes -> boundary emitted for previous domain
    out = s.observe("2000", "agent")
    assert out is not None
    domain, boundary_ts, dwell_ms, evidence = out
    assert domain == "state"
    assert boundary_ts == "2000"
    assert dwell_ms == 1000
    assert evidence == "leader_change"


def test_segmenter_max_dwell():
    s = Segmenter(max_dwell_ms=1500)
    assert s.observe("1000", "state") is None
    # Same leader, below dwell threshold -> no boundary
    assert s.observe("2000", "state") is None
    # Reach dwell threshold -> boundary for same domain (max_dwell)
    out = s.observe("2600", "state")
    assert out is not None
    domain, boundary_ts, dwell_ms, evidence = out
    assert domain == "state"
    assert boundary_ts == "2600"
    assert dwell_ms == 1600
    assert evidence == "max_dwell"

