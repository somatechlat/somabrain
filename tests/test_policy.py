import os
import sys
from importlib import import_module

from fastapi.testclient import TestClient


def main():
    # Kill switch deny
    os.environ["SOMABRAIN_KILL_SWITCH"] = "on"
    for m in list(sys.modules.keys()):
        if m.startswith("somabrain"):
            sys.modules.pop(m, None)
    app_mod = import_module("somabrain.app")
    app = app_mod.app
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 503

    # Review on missing provenance for write
    os.environ.pop("SOMABRAIN_KILL_SWITCH", None)
    for m in list(sys.modules.keys()):
        if m.startswith("somabrain"):
            sys.modules.pop(m, None)
    app_mod = import_module("somabrain.app")
    app = app_mod.app
    client = TestClient(app)
    r = client.post(
        "/remember",
        json={"coord": None, "payload": {"task": "write x", "memory_type": "episodic"}},
    )
    # allowed but tagged as review (middleware sets header)
    assert r.status_code in (200, 503)
    if r.status_code == 200:
        assert r.headers.get("X-Policy-Review") == "true"
    print("Policy tests passed.")


if __name__ == "__main__":
    sys.path.insert(0, ".")
    main()
