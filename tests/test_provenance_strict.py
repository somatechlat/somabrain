import os
import sys
from importlib import import_module

from fastapi.testclient import TestClient


def main():
    os.environ["SOMABRAIN_REQUIRE_PROVENANCE"] = "true"
    os.environ["SOMABRAIN_PROVENANCE_STRICT_DENY"] = "true"
    for m in list(sys.modules.keys()):
        if m.startswith("somabrain"):
            sys.modules.pop(m, None)
    app_mod = import_module("somabrain.app")
    app = app_mod.app
    client = TestClient(app)

    body = {"coord": None, "payload": {"task": "pv2", "memory_type": "episodic"}}
    r = client.post("/remember", json=body)
    assert r.status_code in (503, 200)
    if r.status_code == 200:
        assert r.headers.get("X-Policy-Review") == "true"
    print("Provenance strict test passed.")


if __name__ == "__main__":
    sys.path.insert(0, ".")
    main()
