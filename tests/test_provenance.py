import hashlib
import hmac
import json
import os
import sys
from importlib import import_module

from fastapi.testclient import TestClient


def hmac_header(secret: str, body: dict) -> str:
    b = json.dumps(body, separators=(",", ":"), sort_keys=True).encode("utf-8")
    mac = hmac.new(secret.encode("utf-8"), b, hashlib.sha256).hexdigest()
    return f"hmac-sha256={mac}"


def main():
    os.environ["SOMABRAIN_REQUIRE_PROVENANCE"] = "true"
    os.environ["SOMABRAIN_PROVENANCE_SECRET"] = "topsecret"
    for m in list(sys.modules.keys()):
        if m.startswith("somabrain"):
            sys.modules.pop(m, None)
    app_mod = import_module("somabrain.app")
    app = app_mod.app
    client = TestClient(app)

    # Missing header -> review (but allowed)
    body = {"coord": None, "payload": {"task": "pv1", "memory_type": "episodic"}}
    r = client.post("/remember", json=body)
    assert r.status_code in (200, 503)
    if r.status_code == 200:
        assert r.headers.get("X-Policy-Review") == "true"

    # Valid HMAC -> allowed without review
    hdr = hmac_header("topsecret", body)
    r2 = client.post("/remember", json=body, headers={"X-Provenance": hdr})
    assert r2.status_code == 200
    assert r2.headers.get("X-Policy-Review") is None
    print("Provenance test passed.")


if __name__ == "__main__":
    sys.path.insert(0, ".")
    main()
