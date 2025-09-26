import json

from somabrain.scripts import replay_journal as replay


def write_journal_file(tmp_path, name, events):
    p = tmp_path / name
    with p.open("w", encoding="utf-8") as f:
        for ev in events:
            wrapper = {"kafka_topic": "soma.audit", "event": ev}
            f.write(json.dumps(wrapper) + "\n")
    return p


def test_replay_dry_run_creates_checkpoint(tmp_path):
    jdir = tmp_path / "journal"
    jdir.mkdir()
    ev1 = {"event_id": "e1", "action": "a", "ts": 1}
    ev2 = {"event_id": "e2", "action": "a", "ts": 2}
    write_journal_file(jdir, "test.jsonl", [ev1, ev2])
    cp = tmp_path / "checkpoint.json"
    replay.replay(jdir, cp, dry_run=True, batch=1)
    assert cp.exists()
    data = json.loads(cp.read_text())
    assert "test.jsonl" in data
    assert data["test.jsonl"]["offset"] >= 1


def test_replay_resume(tmp_path):
    jdir = tmp_path / "journal"
    jdir.mkdir()
    evs = [{"event_id": f"e{i}", "action": "a", "ts": i} for i in range(1, 6)]
    write_journal_file(jdir, "t.jsonl", evs)
    cp = tmp_path / "cp.json"
    # process first two by running with batch=2
    replay.replay(jdir, cp, dry_run=True, batch=2)
    data = json.loads(cp.read_text())
    off = data.get("t.jsonl", {}).get("offset", 0)
    assert off >= 1
    # run again; it should resume and update
    replay.replay(jdir, cp, dry_run=True, batch=2)
    data2 = json.loads(cp.read_text())
    assert data2.get("t.jsonl", {}).get("offset", 0) >= off
