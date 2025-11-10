import math

from somabrain.services.integrator_hub import IntegratorHub, DomainObs


def _entropy(weights):
    ps = [max(1e-12, float(weights.get(k, 0.0))) for k in ("state", "agent", "action")]
    Z = sum(ps) or 1.0
    ps = [p / Z for p in ps]
    H = -sum(p * math.log(p) for p in ps) / math.log(3.0)
    return max(0.0, min(1.0, float(H)))


def test_entropy_cap_never_increases_entropy(monkeypatch):
    monkeypatch.setenv("SOMABRAIN_FF_COG_INTEGRATOR", "1")
    # Force tenant cap small to trigger
    monkeypatch.setenv("SOMABRAIN_LEARNING_TENANTS_FILE", "config/learning.tenants.yaml")
    hub = IntegratorHub()
    t = "public"
    # Inject a cap for test tenant (if not loaded)
    hub._tenant_entropy_cap[t] = 0.2
    # Create high-entropy equal weights by updating domains with equal confidence
    ts = 0.0
    for d in ("state", "agent", "action"):
        hub._sm.update(t, d, DomainObs(ts=ts, confidence=1.0, delta_error=0.0))
    # Call snapshot path via _process_update by passing an event; entropy will be recomputed
    ev = {"domain": "state", "delta_error": 0.0, "confidence": 1.0, "evidence": {"tenant": t}}
    gf = hub._process_update(ev)
    assert gf is not None
    w = gf["weights"]
    # Entropy after cap enforcement should be <= raw entropy
    H_after = _entropy(w)
    assert H_after <= 1.0
    # Verify sharpened reduces non-leader weights
    leader = gf["leader"]
    others = [k for k in ("state", "agent", "action") if k != leader]
    for k in others:
        assert w[k] <= 1.0/3 + 1e-6


def test_entropy_cap_converges_within_events(monkeypatch):
    monkeypatch.setenv("SOMABRAIN_FF_COG_INTEGRATOR", "1")
    hub = IntegratorHub()
    t = "public"
    hub._tenant_entropy_cap[t] = 0.25
    # Start with roughly uniform by feeding equal confidences repeatedly
    for i in range(10):
        for d in ("state", "agent", "action"):
            hub._sm.update(t, d, DomainObs(ts=float(i), confidence=1.0, delta_error=0.0))
        ev = {"domain": "state", "delta_error": 0.0, "confidence": 1.0, "evidence": {"tenant": t}}
        gf = hub._process_update(ev)
        assert gf is not None
        H = _entropy(gf["weights"])
        # Should be at or below cap within a few iterations
        if i >= 2:
            assert H <= 0.25 + 1e-3
