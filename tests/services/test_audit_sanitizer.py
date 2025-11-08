import json
from somabrain import audit


def test_sanitize_masks_common_secret_fields():
    payload = {
        "tenant": "secret-token-123",
        "Authorization": "Bearer verysecrettoken",
        "api_key": "abcd1234abcd1234",
        "nested": {"password": "p@ssw0rd!", "ok": 1},
        "list": [
            {"refresh_token": "xyzxyzxyzxyzxyzxyz"},
            {"note": "fine"},
        ],
    }
    out = audit._sanitize_event(payload)
    assert out is not None
    # tenant masked by heuristic
    assert out["tenant"] == audit._MASK
    # authorization preserves scheme but masks token
    assert out["Authorization"].startswith("Bearer ") and out["Authorization"].endswith(
        audit._MASK
    )
    # typical secret-like keys masked
    assert out["api_key"] == audit._MASK
    assert out["nested"]["password"] == audit._MASK
    # list traversal
    assert out["list"][0]["refresh_token"] == audit._MASK
    assert out["list"][1]["note"] == "fine"


def test_publish_event_sanitizes_before_journal(tmp_path, monkeypatch):
    # Force direct journal path
    monkeypatch.setenv("SOMA_AUDIT_JOURNAL_DIR", str(tmp_path))
    # Ensure we do not enforce external backends during this unit test
    monkeypatch.setenv("SOMABRAIN_REQUIRE_EXTERNAL_BACKENDS", "0")
    # Disable Kafka path by simulating no bootstrap
    monkeypatch.setenv("SOMABRAIN_KAFKA_URL", "")
    # Publish an event with secrets
    ev = {
        "event_type": "test",
        "tenant": "secret-token-123",
        "details": {"api_key": "abcd1234abcd1234"},
    }
    ok = audit.publish_event(ev, topic="test.audit")
    assert ok is True
    # Verify journal contains masked content
    p = tmp_path / "audit.jsonl"
    data = p.read_text().strip().splitlines()
    assert data
    last = json.loads(data[-1])
    # payload is wrapped under {"kafka_topic": ..., "event": {...}}
    evt = last["event"]
    assert evt["tenant"] == audit._MASK
    assert evt["details"]["api_key"] == audit._MASK
