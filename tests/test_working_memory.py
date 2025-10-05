from somabrain.runtime.working_memory import WorkingMemoryBuffer


def test_working_memory_fallback_records_in_memory(monkeypatch):
    # Force redis absence
    import somabrain.runtime.working_memory as wm

    monkeypatch.setattr(wm, "redis", None)
    buf = WorkingMemoryBuffer(
        redis_url="redis://localhost:0", ttl_seconds=1, max_items=2
    )
    buf.record("session", {"ts": 1, "value": "a"})
    buf.record("session", {"ts": 2, "value": "b"})
    buf.record("session", {"ts": 3, "value": "c"})
    snap = buf.snapshot("session")
    assert len(snap) == 2
    assert snap[0]["value"] == "b"
    assert snap[1]["value"] == "c"
    buf.clear("session")
    assert buf.snapshot("session") == []
