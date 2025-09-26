import importlib.util
from pathlib import Path

from somabrain.config import Config
from somabrain.journal import append_event
from somabrain.memory_client import MemoryClient

# Load the script module directly since `scripts/` is not a package
script_path = (
    Path(__file__).resolve().parents[1] / "scripts" / "migrate_journal_to_backend.py"
)
spec = importlib.util.spec_from_file_location(
    "migrate_journal_to_backend", str(script_path)
)
mig_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mig_mod)  # type: ignore[attr-defined]
migrate_journal = mig_mod.migrate_journal


def test_migrate_journal_idempotent(tmp_path):
    base = str(tmp_path)
    ns = "testns"

    # Create some events
    ev1 = {"type": "mem", "key": "k1", "payload": {"v": 1}}
    ev2 = {"type": "mem", "key": "k2", "payload": {"v": 2}}
    ev3 = {
        "type": "link",
        "from": [0.1, 0.2, 0.3],
        "to": [0.4, 0.5, 0.6],
        "link_type": "related",
        "weight": 1.0,
    }

    append_event(base, ns, ev1)
    append_event(base, ns, ev2)
    append_event(base, ns, ev3)

    cfg = Config(
        namespace=ns,
        persistent_journal_enabled=True,
        journal_dir=base,
    )
    # Disable external HTTP endpoint so MemoryClient falls back to in-process stub.
    cfg.http.endpoint = ""
    client = MemoryClient(cfg)

    mem_added, link_added = migrate_journal(base, ns, client)
    assert mem_added == 2
    assert link_added == 1

    # Running again should find nothing to add
    mem_added2, link_added2 = migrate_journal(base, ns, client)
    assert mem_added2 == 0
    assert link_added2 == 0
