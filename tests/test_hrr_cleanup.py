import sys
from importlib import import_module


def main():
    # Import app and wire HRR manually (Dynaconf may be unavailable)
    app_mod = import_module("somabrain.app")
    app = app_mod.app
    # Force-enable HRR cleanup
    app_mod.cfg.use_hrr_cleanup = True
    # Create HRR context if missing
    if app_mod.quantum is None:
        from somabrain.quantum import HRRConfig, QuantumLayer

        app_mod.quantum = QuantumLayer(HRRConfig())
    if getattr(app_mod, "mt_ctx", None) is None:
        from somabrain.context_hrr import HRRContextConfig
        from somabrain.mt_context import MultiTenantHRRContext

        app_mod.mt_ctx = MultiTenantHRRContext(
            app_mod.quantum, HRRContextConfig(), max_tenants=1000
        )

    from fastapi.testclient import TestClient

    client = TestClient(app)

    # Seed anchor via remember (also admits into HRR context when HRR is present)
    payload = {"task": "anchor task", "importance": 1, "memory_type": "episodic"}
    r = client.post("/remember", json={"coord": None, "payload": payload})
    assert r.status_code == 200, r.text

    # Recall with HRR cleanup enabled
    r = client.post("/recall", json={"query": "anchor task", "top_k": 2})
    assert r.status_code == 200, r.text
    data = r.json()
    assert "hrr_cleanup" in data
    hc = data["hrr_cleanup"]
    assert isinstance(hc.get("anchor_id", ""), str)
    score = float(hc.get("score", 0.0))
    assert 0.0 <= score <= 1.0

    # Metrics include cleanup counters
    r = client.get("/metrics")
    assert r.status_code == 200
    text = r.text
    assert "somabrain_hrr_cleanup_used_total" in text

    print("HRR cleanup test passed.")


if __name__ == "__main__":
    # Ensure local imports resolve when running directly
    sys.path.insert(0, ".")
    main()
