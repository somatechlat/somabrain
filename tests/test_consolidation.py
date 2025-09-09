import sys
from importlib import import_module

from fastapi.testclient import TestClient


def main():
    app_mod = import_module("somabrain.app")
    app = app_mod.app
    client = TestClient(app)

    # Seed episodics
    for t in ["dream alpha", "dream beta", "dream gamma", "dream delta"]:
        r = client.post(
            "/remember",
            json={
                "coord": None,
                "payload": {"task": t, "importance": 2, "memory_type": "episodic"},
            },
        )
        assert r.status_code == 200

    # Run NREM and REM via module functions
    cons = import_module("somabrain.consolidation")
    stats_n = cons.run_nrem(
        "public",
        app_mod.cfg,
        app_mod.mt_wm,
        app_mod.mt_memory,
        top_k=3,
        max_summaries=2,
    )
    assert stats_n["created"] >= 1
    stats_r = cons.run_rem(
        "public",
        app_mod.cfg,
        app_mod.mt_wm,
        app_mod.mt_memory,
        recomb_rate=0.5,
        max_summaries=2,
    )
    assert stats_r["created"] >= 1

    # Check metrics expose consolidation counters
    m = client.get("/metrics")
    assert m.status_code == 200
    text = m.text
    assert "somabrain_consolidation_runs_total" in text
    assert "somabrain_consolidation_rem_synthesized_total" in text
    print("Consolidation tests passed.")


if __name__ == "__main__":
    sys.path.insert(0, ".")
    main()
