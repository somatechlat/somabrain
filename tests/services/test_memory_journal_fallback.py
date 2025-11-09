from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from somabrain.services.memory_service import MemoryService


class FailingBackend:
    def __init__(self):
        self._outbox_path = None

    # Interface expected by MemoryService.client()
    def remember(self, key, payload):
        raise RuntimeError("backend down")

    async def aremember(self, key, payload):
        raise RuntimeError("backend down")

    def health(self):
        return {"http": False}

    # Methods used by outbox replay; not exercised in this test
    def remember_bulk(self, items, request_id=None):
        raise RuntimeError("backend down")

    def link(self, *args, **kwargs):
        raise RuntimeError("backend down")


class FakeMT:
    def __init__(self):
        self.backend = FailingBackend()

    def for_namespace(self, ns):
        return self.backend


@pytest.mark.unit
def test_journal_fallback_writes_event(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Enable journal fallback and disable strict external backend requirement
    monkeypatch.setenv("ALLOW_JOURNAL_FALLBACK", "1")
    monkeypatch.delenv("SOMABRAIN_REQUIRE_EXTERNAL_BACKENDS", raising=False)

    # Point config.journal_dir to a temporary directory
    from somabrain import config as cfg_mod

    cfg = cfg_mod.load_config()
    cfg.journal_dir = str(tmp_path)

    # Patch get_config in both config module and memory_service module to return our modified instance
    monkeypatch.setattr(cfg_mod, "get_config", lambda: cfg)
    import somabrain.services.memory_service as mem_svc_mod

    monkeypatch.setattr(mem_svc_mod, "get_config", lambda: cfg)

    svc = MemoryService(mt_memory=FakeMT(), namespace="testns")

    # Attempt to remember; this should raise but also journal the failure
    payload = {"task": "journal smoke", "memory_type": "episodic", "importance": 1}
    with pytest.raises(RuntimeError):
        svc.remember("key-1", payload)

    # Verify a JSONL file was created and contains our payload
    journal_file = tmp_path / "testns.jsonl"
    assert journal_file.exists()
    data = journal_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(data) >= 1
    rec = json.loads(data[-1])
    assert rec.get("op") in {"remember", "mem"}
    inner = rec.get("payload") or {}
    assert inner.get("task") == "journal smoke"
