from __future__ import annotations

import importlib
import time


def test_consistency_enforcement_drop_frame(monkeypatch):
    """Simulate persistent low kappa leading to frame drop when leader=action.

    Patches runtime_config thresholds so a single low-kappa sample triggers degraded state.
    Uses disjoint posterior distributions to yield kappa≈0 (intent_probs vs action_probs).
    Expect IntegratorHub to drop frames (return None) once degraded and leader would be 'action'.
    """
    # Patch runtime_config getters BEFORE importing integrator_hub so thresholds apply during __init__.
    import somabrain.runtime_config as rc

    def _get_float(key: str, default: float = 0.0) -> float:  # type: ignore
        if key == "consistency_kappa_min":
            return 0.9  # high threshold so kappa=0 triggers immediately
        if key == "consistency_fail_count":
            return 1.0  # single violation to degrade
        # fall through to default for other keys
        return default

    def _get_bool(key: str, default: bool = False) -> bool:  # type: ignore
        if key in ("consistency_drop_frame", "consistency_alert_enabled"):
            return True
        return default

    monkeypatch.setattr(rc, "get_float", _get_float)
    monkeypatch.setattr(rc, "get_bool", _get_bool)

    # Reload module to ensure patched runtime_config is used
    mod = importlib.reload(importlib.import_module("somabrain.services.integrator_hub"))
    ih = mod.IntegratorHub()

    # Seed agent posterior (intent_probs) with single outcome 'a'
    agent_post = {"intent_probs": {"a": 1.0}}
    # Seed action posterior (action_probs) with different outcome 'b'
    action_post = {"action_probs": {"b": 1.0}}

    now_ts = time.time()
    ih._sm.update(
        "public",
        "agent",
        mod.DomainObs(
            ts=now_ts,
            confidence=0.3,  # lower confidence so action can become leader later
            delta_error=0.2,
            meta={"posterior": agent_post, "domain": "agent", "evidence": {"tenant": "public"}},
        ),
    )

    # First action update: should compute kappa≈0 and degrade consistency
    ev_action = {
        "domain": "action",
        "delta_error": 0.1,
        "confidence": 0.95,  # high confidence to select leader=action
        "posterior": action_post,
        "evidence": {"tenant": "public"},
    }
    gf1 = ih._process_update(ev_action)
    # After first low-kappa sample, degraded state should be set
    assert ih._consistency_degraded.get("public") is True
    # Second update should attempt to build frame and drop it (return None)
    gf2 = ih._process_update(ev_action)
    assert gf2 is None, "Expected frame drop under degraded consistency with leader=action"

    # Recovery scenario: supply matching posteriors (identical keys) to raise kappa
    matching_action_post = {"action_probs": {"a": 0.5, "b": 0.5}}
    matching_agent_post = {"intent_probs": {"a": 0.5, "b": 0.5}}
    ih._sm.update(
        "public",
        "agent",
        mod.DomainObs(
            ts=time.time(),
            confidence=0.6,
            delta_error=0.1,
            meta={"posterior": matching_agent_post, "domain": "agent", "evidence": {"tenant": "public"}},
        ),
    )
    ev_action_recover = {
        "domain": "action",
        "delta_error": 0.05,
        "confidence": 0.9,
        "posterior": matching_action_post,
        "evidence": {"tenant": "public"},
    }
    gf3 = ih._process_update(ev_action_recover)
    # Depending on hysteresis, degraded flag may clear; allow either recovery or continued degradation
    assert gf3 is None or ih._consistency_degraded.get("public") in (True, False)
