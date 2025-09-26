import json

import pytest

import somabrain.audit as audit
import somabrain.metrics as metrics


@pytest.fixture(autouse=True)
def reset_registry():
    # Ensure a fresh metrics registry for each test
    from prometheus_client import CollectorRegistry

    new_registry = CollectorRegistry()
    # Replace both the module-level registry and the legacy REGISTRY used by helpers
    metrics.registry = new_registry
    # The metrics module also defines a global REGISTRY variable; patch it as well
    if hasattr(metrics, "REGISTRY"):
        metrics.REGISTRY = new_registry
    # Recreate metrics used in audit
    metrics.AUDIT_KAFKA_PUBLISH = metrics.get_counter(
        "somabrain_audit_kafka_publish_total",
        "Audit events successfully published to Kafka (best-effort)",
    )
    metrics.AUDIT_JOURNAL_FALLBACK = metrics.get_counter(
        "somabrain_audit_journal_fallback_total",
        "Audit events written to the durable JSONL journal as a fallback",
    )
    metrics.JOURNAL_SKIP = metrics.get_counter(
        "somabrain_journal_skip_total",
        "Journal events skipped due to errors",
    )
    yield


def test_publish_fallback_to_journal(tmp_path, monkeypatch):
    # Force audit to think no Kafka client is available
    monkeypatch.setattr(audit, "_DEFAULT_KAFKA_CLIENT", "none")
    # Use a temporary journal directory
    journal_dir = tmp_path / "journal"
    journal_dir.mkdir()
    monkeypatch.setenv("SOMA_AUDIT_JOURNAL_DIR", str(journal_dir))
    # Ensure Kafka URL is empty to trigger fallback path
    monkeypatch.setenv("SOMA_KAFKA_URL", "invalid://")
    event = {"event_id": "test1", "action": "test", "ts": 1234567890}
    # Ensure the kafka import fails to trigger the fallback path
    import sys

    # Remove any existing kafka module entry if present
    if "kafka" in sys.modules:
        del sys.modules["kafka"]
    # Mock the journal.append_event to capture the call instead of writing to disk
    import somabrain.journal as audit_journal

    called = []

    def fake_append_event(base_dir, namespace, payload):
        called.append((base_dir, namespace, payload))

    # Patch the function used inside publish_event
    sys.modules["somabrain.journal"] = audit_journal  # ensure module is loaded
    audit_journal.append_event = fake_append_event
    # Also patch _audit_journal_dir to return our temporary dir (though not used when append_event is mocked)
    monkeypatch.setattr(audit, "_audit_journal_dir", lambda: journal_dir)
    # Now call publish_event which should hit the fallback path
    result = audit.publish_event(event)
    assert result is True
    # Ensure the mocked append_event was called
    assert called, "append_event should have been called for journal fallback"


def test_publish_event_falls_back_to_journal(tmp_path, monkeypatch):
    # Force journal dir to tmp
    jdir = tmp_path / "journal"
    monkeypatch.setenv("SOMA_AUDIT_JOURNAL_DIR", str(jdir))
    # Ensure Kafka isn't available by setting SOMA_KAFKA_URL to invalid
    monkeypatch.setenv("SOMA_KAFKA_URL", "kafka://127.0.0.1:9999")

    ev = {"action": "test.action", "source": "tests"}
    ok = audit.publish_event(ev, topic="soma.audit")
    assert ok is True
    # check that a file exists in journal dir
    files = list(jdir.glob("*.jsonl"))
    assert len(files) >= 1
    # inspect the first file's first line
    with files[0].open("r", encoding="utf-8") as f:
        line = f.readline().strip()
    data = json.loads(line)
    # journal stores wrapper with kafka_topic + event
    assert data.get("event") is not None
    assert data["event"].get("event_id") is not None
    assert data["event"].get("schema_version") == "audit_event_v1"
