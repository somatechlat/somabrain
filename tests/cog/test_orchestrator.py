from __future__ import annotations

import json
from typing import Any, Dict, List

import pytest

from somabrain.services.orchestrator_service import (
    OrchestratorService,
    _parse_global_frame,
    _parse_segment_boundary,
)


def test_parse_global_frame_json_ok():
    msg = {
        "ts": "2025-01-01T00:00:00Z",
        "leader": "plan",
        "weights": {"plan": 0.9, "act": 0.1},
        "frame": {"tenant": "t1", "foo": "bar"},
        "rationale": "softmax",
    }
    raw = json.dumps(msg).encode("utf-8")
    gf = _parse_global_frame(raw, None)
    assert gf is not None
    assert gf.tenant == "t1"
    assert gf.leader == "plan"
    assert gf.weights["plan"] == pytest.approx(0.9)
    assert gf.frame["foo"] == "bar"


def test_parse_global_frame_missing_fields_returns_none():
    raw = json.dumps({"ts": "", "leader": ""}).encode("utf-8")
    assert _parse_global_frame(raw, None) is None


def test_parse_segment_boundary_json_ok():
    msg = {
        "tenant": "t1",
        "domain": "plan",
        "boundary_ts": 1735689600000,
        "dwell_ms": 1200,
        "evidence": {"change": True},
    }
    raw = json.dumps(msg).encode("utf-8")
    sb = _parse_segment_boundary(raw, None)
    assert isinstance(sb, dict)
    assert sb["tenant"] == "t1"
    assert sb["domain"] == "plan"


def test_orchestrator_enqueues_snapshot(monkeypatch):
    events: List[Dict[str, Any]] = []

    def fake_enqueue_event(
        topic: str,
        payload: Dict[str, Any],
        dedupe_key: str | None = None,
        tenant_id: str | None = None,
        session=None,
    ):
        events.append(
            {
                "topic": topic,
                "payload": payload,
                "dedupe_key": dedupe_key,
                "tenant_id": tenant_id,
            }
        )

    # Monkeypatch the module-level symbol
    import somabrain.services.orchestrator_service as mod

    monkeypatch.setattr(mod, "enqueue_event", fake_enqueue_event)

    svc = OrchestratorService()

    # Seed GF context for tenant t1
    gf_raw = json.dumps(
        {
            "ts": "2025-01-01T00:00:10Z",
            "leader": "plan",
            "weights": {"plan": 0.8, "act": 0.2},
            "frame": {"tenant": "t1", "foo": "bar"},
            "rationale": "ok",
        }
    ).encode("utf-8")
    gf = _parse_global_frame(gf_raw, None)
    assert gf is not None
    svc._ctx["t1"] = gf  # type: ignore[attr-defined]

    # Boundary arrives for t1 -> enqueue
    sb = {
        "tenant": "t1",
        "domain": "plan",
        "boundary_ts": 1735689600000,
        "dwell_ms": 1200,
        "evidence": {"change": True},
    }

    svc._remember_snapshot("t1", sb)  # type: ignore[attr-defined]

    assert len(events) == 1
    ev = events[0]
    assert ev["topic"] == "memory.episodic.snapshot"
    p = ev["payload"]
    assert p["tenant"] == "t1"
    assert p["namespace"]
    assert p["value"]["segment"]["domain"] == "plan"
    assert p["value"]["leader"] == "plan"  # carries last frame context
