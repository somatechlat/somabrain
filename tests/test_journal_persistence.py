from __future__ import annotations

import shutil
import tempfile

from somabrain.config import Config
from somabrain.journal import append_event, journal_path
from somabrain.memory_pool import MultiTenantMemory


def test_journal_replay_across_restart():
    tmp = tempfile.mkdtemp(prefix="sb_journal_")
    try:
        ns = "test_ns"
        # configure stub mode with journaling enabled
        cfg = Config(
            namespace=ns,
            persistent_journal_enabled=True,
            journal_dir=tmp,
        )
        cfg.http.endpoint = ""

        # append a memory and a link event to journal directly (simulating API writes)
        append_event(
            tmp,
            ns,
            {
                "type": "mem",
                "key": "hello",
                "payload": {"task": "hello world", "universe": "real"},
            },
        )
        # deterministic coordinates for link using the client helper
        from somabrain.memory_client import MemoryClient

        mc_probe = MemoryClient(cfg)
        a = mc_probe.coord_for_key("hello", universe="real")
        b = mc_probe.coord_for_key("world", universe="real")
        append_event(
            tmp,
            ns,
            {"type": "link", "from": a, "to": b, "link_type": "related", "weight": 1.0},
        )

        # first construction should replay journal into client
        pool = MultiTenantMemory(cfg)
        client = pool.for_namespace(ns)
        # recall should include the stored payload (stub returns recent)
        hits = client.recall("hello", top_k=5)
        assert any("hello" in str(h.payload.get("task", "")) for h in hits)

        # and link should be present in local graph
        links = client.links_from(a, limit=10)
        found = False
        for x in links:
            t = x.get("to")
            if isinstance(t, (list, tuple)) and tuple(t) == tuple(b):
                found = True
                break
        assert found

        # rotation should create a .1 and new file
        from somabrain.journal import rotate_journal

        size = journal_path(tmp, ns).stat().st_size
        rot = rotate_journal(tmp, ns, max_bytes=max(0, size - 1), keep=2)
        assert rot is not None and rot.exists()
        assert journal_path(tmp, ns).exists()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_journal_compaction():
    tmp = tempfile.mkdtemp(prefix="sb_journal_")
    try:
        ns = "test_compact"
        # write multiple mem events with same key and link duplicates
        append_event(tmp, ns, {"type": "mem", "key": "k1", "payload": {"task": "t1"}})
        append_event(tmp, ns, {"type": "mem", "key": "k1", "payload": {"task": "t2"}})
        # link duplicates
        a = (0.1, 0.2, 0.3)
        b = (0.4, 0.5, 0.6)
        append_event(
            tmp,
            ns,
            {"type": "link", "from": a, "to": b, "link_type": "related", "weight": 0.7},
        )
        append_event(
            tmp,
            ns,
            {"type": "link", "from": a, "to": b, "link_type": "related", "weight": 0.8},
        )
        from somabrain.journal import compact_journal

        ok = compact_journal(tmp, ns)
        assert ok is True
        # verify compacted contents
        from somabrain.journal import iter_events

        evs = list(iter_events(tmp, ns))
        # expect 2 records: latest mem and one link with accumulated weight
        assert len(evs) == 2
        mem_ev = next(e for e in evs if e.get("type") == "mem")
        link_ev = next(e for e in evs if e.get("type") == "link")
        assert mem_ev.get("payload", {}).get("task") == "t2"
        assert abs(float(link_ev.get("weight") or 0.0) - 1.5) < 1e-6
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
