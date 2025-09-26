import json
import os
from importlib import import_module

from fastapi.testclient import TestClient

from somabrain import config as _cfg_mod

app_mod = import_module("somabrain.app")
app = app_mod.app
client = TestClient(app)


def test_neuromodulators_admin_auth_and_audit(tmp_path, monkeypatch):
    # Configure an API token via monkeypatching the loaded config
    token = "secret-token-123"
    # Monkeypatch cfg.api_token used by app (cfg is module-level in somabrain.app)
    app_mod.cfg.api_token = token

    # Remove any existing audit file
    audit_path = getattr(
        _cfg_mod.load_config(), "audit_log_path", "./data/somabrain/audit.log"
    )
    try:
        os.remove(audit_path)
    except Exception:
        pass

    # POST without Authorization -> 401
    r = client.post(
        "/neuromodulators",
        json={
            "dopamine": 0.1,
            "serotonin": 0.2,
            "noradrenaline": 0.01,
            "acetylcholine": 0.1,
        },
    )
    assert r.status_code in (401, 403)

    # POST with wrong token -> 403
    r = client.post(
        "/neuromodulators",
        json={
            "dopamine": 0.1,
            "serotonin": 0.2,
            "noradrenaline": 0.01,
            "acetylcholine": 0.1,
        },
        headers={"Authorization": "Bearer wrong"},
    )
    assert r.status_code == 403

    # POST with correct token -> 200
    r = client.post(
        "/neuromodulators",
        json={
            "dopamine": 0.11,
            "serotonin": 0.21,
            "noradrenaline": 0.02,
            "acetylcholine": 0.12,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200

    # Audit log should contain an entry
    try:
        with open(audit_path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f.readlines() if line.strip()]
            assert len(lines) >= 1
            ev = json.loads(lines[-1])
            assert ev.get("action") == "neuromodulators_set"
    except FileNotFoundError:
        # If audit path missing, test how audit helper defaults; tolerate missing file but warn
        assert False, f"Audit file {audit_path} not found"
