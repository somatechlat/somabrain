import os
import sys
from importlib import import_module

from fastapi.testclient import TestClient


def main():
    os.environ["SOMABRAIN_USE_DRIFT_MONITOR"] = "true"
    for m in list(sys.modules.keys()):
        if m.startswith("somabrain"):
            sys.modules.pop(m, None)
    app_mod = import_module("somabrain.app")
    app = app_mod.app
    client = TestClient(app)

    # First recall (establish baseline)
    r1 = client.post("/recall", json={"query": "alpha baseline", "top_k": 1})
    assert r1.status_code == 200
    d1 = r1.json().get("drift", {})
    assert isinstance(d1, dict)

    # Second recall with different query; ensure drift field exists
    r2 = client.post("/recall", json={"query": "ZULU QUIRK JUMP FOXTROT", "top_k": 1})
    assert r2.status_code == 200
    d2 = r2.json().get("drift", {})
    assert isinstance(d2, dict)
    assert "score" in d2
    print("Drift monitor test passed.")


if __name__ == "__main__":
    sys.path.insert(0, ".")
    main()
