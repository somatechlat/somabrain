"""Behavioral/contract tests for outbox PK and constitution fail-closed (ADV C1/C2/C4).

These read source as text so they run without Django settings.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_enqueue_memory_event_returns_int_pk() -> None:
    src = _read("somabrain/db/outbox.py")
    assert "-> int:" in src
    assert "return int(event.id)" in src
    assert "return dedupe_key" not in src


def test_mark_events_for_replay_takes_event_ids() -> None:
    src = _read("somabrain/db/outbox.py")
    assert "def mark_events_for_replay(event_ids: Sequence[int]) -> int:" in src
    assert "id__in=ids" in src


def test_memory_remember_uses_event_id() -> None:
    src = _read("somabrain/api/endpoints/memory_remember.py")
    assert "event_id = await sync_to_async(enqueue_memory_event)" in src
    assert "dedupe_key = await sync_to_async(enqueue_memory_event)" not in src
    assert "mark_event_sent)(event_id)" in src


def test_remember_returns_event_id() -> None:
    src = _read("somabrain/memory/remember.py")
    assert "event_id = enqueue_memory_event(" in src
    assert "return event_id" in src


def test_constitution_opa_failure_denies() -> None:
    src = _read("somabrain/constitution/__init__.py")
    assert "opa evaluation failed" in src
    # Must deny on OPA exception, not fall through to local-pass
    assert 'result = {\n                    "allowed": False,' in src or '"allowed": False' in src
    idx = src.find("local opa eval failed")
    assert idx == -1 or "opa evaluation failed" in src


def test_admin_calls_replay_with_ids() -> None:
    admin = _read("somabrain/api/endpoints/admin.py")
    mem_admin = _read("somabrain/api/endpoints/memory_admin.py")
    assert "mark_events_for_replay(body.event_ids)" in admin
    assert "mark_events_for_replay(payload.ids)" in mem_admin
