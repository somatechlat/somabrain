from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from somabrain.journal import append_event, journal_path

script_path = Path(__file__).resolve().parents[1] / "scripts" / "journal_to_outbox.py"
spec = importlib.util.spec_from_file_location("journal_to_outbox", str(script_path))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)  # type: ignore[attr-defined]


def test_journal_to_outbox_migration(tmp_path):
    journal_dir = tmp_path / "journal"
    journal_dir.mkdir()
    outbox_path = tmp_path / "outbox.jsonl"

    namespace = "tenant_ns"
    append_event(
        str(journal_dir),
        namespace,
        {
            "op": "remember",
            "type": "mem",
            "key": "doc-1",
            "payload": {"task": "hello"},
            "universe": "real",
        },
    )
    append_event(
        str(journal_dir),
        namespace,
        {
            "op": "link",
            "type": "link",
            "from": [0.0, 0.1, 0.2],
            "to": [0.3, 0.4, 0.5],
            "link_type": "related",
            "weight": 1.0,
        },
    )

    events, converted = module.migrate_namespace(
        journal_dir,
        namespace,
        outbox_path,
        dry_run=False,
        archive=True,
    )

    assert events == 2
    assert converted == 2
    assert outbox_path.exists()
    lines = [json.loads(line) for line in outbox_path.read_text().splitlines()]
    assert lines[0]["op"] == "remember"
    assert lines[0]["payload"]["key"] == "doc-1"
    assert lines[1]["op"] == "link"
    # Journal file should be archived
    original_path = journal_path(str(journal_dir), namespace)
    assert not original_path.exists()
    migrated_path = original_path.with_suffix(".jsonl.migrated")
    assert migrated_path.exists()
