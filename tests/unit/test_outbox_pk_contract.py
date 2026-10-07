"""Behavioral/contract tests for outbox PK and constitution fail-closed (ADV C1/C2/C4).

These read source as text so they run without Django settings.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.no_django

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


# ---------------------------------------------------------------------------
# C1-2: idempotency key is mem:{coord} — no operation prefix, no tenant, no UUID
# ---------------------------------------------------------------------------


def test_idempotency_key_is_mem_coord() -> None:
    src = _read("somabrain/db/outbox.py")
    assert 'return f"mem:{_coord_to_str(coord)}"' in src
    # Must NOT hash operation/tenant/extra into the key
    assert "hashlib.sha256" not in src
    assert "parts = [operation, tenant]" not in src


def test_idempotency_key_fails_closed_without_coord() -> None:
    src = _read("somabrain/db/outbox.py")
    assert "if coord is None:" in src
    assert "raise ValueError" in src


def test_enqueue_event_uuid_fallback_removed() -> None:
    src = _read("somabrain/db/outbox.py")
    assert "uuid.uuid4" not in src
    assert "import uuid" not in src
    # Must raise when dedupe_key is absent
    assert "raise ValueError" in src
    assert "dedupe_key is None" in src


def test_mark_events_for_replay_includes_pending() -> None:
    src = _read("somabrain/db/outbox.py")
    assert '"failed", "pending"' in src or "'failed', 'pending'" in src


# ---------------------------------------------------------------------------
# C1-1: publisher writes to the STORE before marking sent (T-6)
# ---------------------------------------------------------------------------


def test_publisher_calls_aremember_before_mark_sent() -> None:
    src = _read("somabrain/workers/outbox_publisher.py")
    assert "aremember" in src
    assert "_write_memory_to_store" in src
    # The store write must come before ev.status = "sent" in the memory.store path
    store_idx = src.find('if ev.topic == "memory.store":')
    assert store_idx != -1, "memory.store branch missing"
    sent_idx = src.find('ev.status = "sent"', store_idx)
    aremember_idx = src.find("_write_memory_to_store(", store_idx)
    assert aremember_idx != -1, "store write call missing"
    assert aremember_idx < sent_idx, "store write must precede mark-sent"


def test_publisher_marks_sent_only_after_store() -> None:
    src = _read("somabrain/workers/outbox_publisher.py")
    # The memory.store path must call _write_memory_to_store BEFORE setting sent
    section = src[src.find("if ev.topic == \"memory.store\":") :]
    section = section[: section.find("else:")]
    write_pos = section.find("_write_memory_to_store(")
    sent_pos = section.find("ev.status = \"sent\"")
    assert write_pos != -1
    assert sent_pos != -1
    assert write_pos < sent_pos


def test_publisher_drain_accepts_agent_coord_payload() -> None:
    """Agent-path rows carry ``coord`` (no ``key``); drain must still write."""
    src = _read("somabrain/workers/outbox_publisher.py")
    assert 'payload.get("key")' in src
    assert 'payload.get("coord")' in src
    # Fail closed when neither key nor coord is present
    assert "neither key nor coord" in src


def test_agent_path_does_not_mix_request_id_into_key() -> None:
    src = _read("somabrain/memory/remember.py")
    assert "extra_key=None" in src
    assert "extra_key=request_id" not in src


def test_promotion_queue_supplies_dedupe_key() -> None:
    """enqueue_event no longer invents a UUID — callers must pass a key."""
    src = _read("somabrain/memory/promotion.py")
    assert "dedupe_key=" in src
    assert "uuid.uuid4" not in src
