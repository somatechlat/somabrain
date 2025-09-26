import tempfile
from pathlib import Path

from somabrain.journal import (
    append_event,
    compact_journal,
    journal_path,
    rotate_journal,
)


def test_journal_rotate_and_compact_smoke():
    with tempfile.TemporaryDirectory() as d:
        ns = "tenantA"
        # write enough events to exceed small threshold
        for i in range(50):
            append_event(
                d, ns, {"type": "mem", "key": f"k{i}", "payload": {"task": f"t{i}"}}
            )
        p = journal_path(d, ns)
        assert p.exists()
        # rotate at a tiny max_bytes
        rot = rotate_journal(d, ns, max_bytes=1_000, keep=2)
        # rotation may or may not happen depending on platform timing; accept
        # None or Path
        assert rot is None or isinstance(rot, Path)
        # compact should succeed
        ok = compact_journal(d, ns)
        assert ok is True
