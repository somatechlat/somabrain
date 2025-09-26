from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

import somabrain.app as app_module

app = app_module.app


@pytest.fixture
def client():
    return TestClient(app)


def _get_etag(resp):
    return resp.headers.get("ETag")


def _compute_etag_from_payload(payload: dict) -> str:
    import hashlib
    import json

    j = json.dumps(payload or {}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(j.encode("utf-8")).hexdigest()


def test_persona_crud_etag_lifecycle(client):
    tenant = "personatest"
    headers = {"X-Tenant-ID": tenant}
    pid = "alice"

    # Create persona
    body = {"id": pid, "display_name": "Alice", "properties": {"mood": "curious"}}
    r = client.put(f"/persona/{pid}", headers=headers, json=body)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("ok") is True
    persona = data.get("persona")
    assert persona and persona.get("id") == pid
    etag1 = _get_etag(r)
    assert etag1 is not None

    # GET returns persona; compute ETag from returned payload (server may
    # normalize/persist the payload differently than the incoming body)
    r2 = client.get(f"/persona/{pid}", headers=headers)
    assert r2.status_code == 200
    p2 = r2.json()
    assert p2.get("id") == pid
    etag_get = _get_etag(r2)
    assert etag_get is not None
    # verify header matches a deterministic hash of the returned payload
    assert etag_get == _compute_etag_from_payload(p2)

    # PUT with wrong If-Match fails (412)
    wrong_etag = "deadbeef"
    body2 = {"id": pid, "display_name": "Alice2", "properties": {"mood": "excited"}}
    r3 = client.put(
        f"/persona/{pid}", headers={**headers, "If-Match": wrong_etag}, json=body2
    )
    assert r3.status_code == 412

    # PUT with correct If-Match succeeds
    r4 = client.put(
        f"/persona/{pid}", headers={**headers, "If-Match": etag_get}, json=body2
    )
    assert r4.status_code == 200

    # Canonicalize: fetch stored representation and compute its ETag
    r5 = client.get(f"/persona/{pid}", headers=headers)
    assert r5.status_code == 200
    p5 = r5.json()
    etag_after_update = _get_etag(r5)
    assert etag_after_update == _compute_etag_from_payload(p5)
    assert etag_after_update != etag_get
    assert p5.get("display_name") == "Alice2"

    # DELETE tombstone
    r6 = client.delete(f"/persona/{pid}", headers=headers)
    assert r6.status_code == 200

    # After delete, GET returns 404
    # (There might be eventual consistency in some backends; retry briefly)
    for _ in range(5):
        r7 = client.get(f"/persona/{pid}", headers=headers)
        if r7.status_code == 404:
            break
        time.sleep(0.1)
    assert r7.status_code == 404
