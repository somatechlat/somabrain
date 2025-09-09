import os
import sys
from importlib import import_module

from fastapi.testclient import TestClient


def main():
    # Force slow provider and short timeout to trigger fallback
    os.environ["SOMABRAIN_PREDICTOR_PROVIDER"] = "slow"
    os.environ["SOMABRAIN_PREDICTOR_TIMEOUT_MS"] = "50"
    # Re-import app to pick up env-based config
    for m in list(sys.modules.keys()):
        if m.startswith("somabrain"):
            sys.modules.pop(m, None)
    app_mod = import_module("somabrain.app")
    app = app_mod.app
    client = TestClient(app)

    r = client.post("/act", json={"task": "budget test", "top_k": 1})
    assert r.status_code == 200
    # Metrics should report fallback >= 1
    m = client.get("/metrics")
    assert m.status_code == 200
    text = m.text
    assert "somabrain_predictor_fallback_total" in text
    print("Predictor budget test passed.")


if __name__ == "__main__":
    sys.path.insert(0, ".")
    main()
