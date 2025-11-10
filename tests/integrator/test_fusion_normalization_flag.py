from __future__ import annotations

import os
import importlib


def test_rationale_includes_fusion_note(monkeypatch):
    monkeypatch.setenv("SOMABRAIN_MODE", "full-local")
    # Fresh import to pick up mode-based defaults
    mod = importlib.import_module("somabrain.services.integrator_hub")
    ih = mod.IntegratorHub()

    # Craft two recent observations with different delta_error to bias fused weights
    now_ts = __import__("time").time()
    ih._sm.update("public", "state", mod.DomainObs(ts=now_ts, confidence=0.2, delta_error=1.0, meta={"domain": "state", "evidence": {"tenant": "public"}}))
    ih._sm.update("public", "agent", mod.DomainObs(ts=now_ts, confidence=0.8, delta_error=0.1, meta={"domain": "agent", "evidence": {"tenant": "public"}}))
    # Seed stats so normalization path computes non-zero std
    s_state = ih._stats["state"]
    s_agent = ih._stats["agent"]
    # Simulate two prior samples to get variance
    for derr in (0.9, 1.1):
        s_state["n"] += 1
        d = derr - s_state["mean"]
        s_state["mean"] += d / s_state["n"]
        s_state["m2"] += d * (derr - s_state["mean"])
    for derr in (0.05, 0.15):
        s_agent["n"] += 1
        d = derr - s_agent["mean"]
        s_agent["mean"] += d / s_agent["n"]
        s_agent["m2"] += d * (derr - s_agent["mean"])

    # Process an update to trigger frame build
    ev = {"domain": "state", "delta_error": 1.0, "confidence": 0.2, "evidence": {"tenant": "public"}}
    gf = ih._process_update(ev)
    assert gf is not None
    assert "rationale" in gf
    assert "fusion=normalized" in gf["rationale"], gf["rationale"]
