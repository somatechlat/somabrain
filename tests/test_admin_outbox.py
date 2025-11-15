from __future__ import annotations

import os
import sys
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

os.environ.setdefault("SOMABRAIN_REQUIRE_EXTERNAL_BACKENDS", "0")
if "somabrain.runtime_module" not in sys.modules:
    sys.modules["somabrain.runtime_module"] = SimpleNamespace(
        embedder=object(),
        mt_wm=object(),
        mc_wm=object(),
        set_singletons=lambda **kwargs: None,
    )

from somabrain import schemas as S
from somabrain.app import admin_list_outbox, admin_replay_outbox
from somabrain.db import outbox as outbox_db


@pytest.mark.asyncio
async def test_admin_outbox_list_filters(monkeypatch):
    captured: dict[str, object] = {}

    def fake_list(status: str, tenant_id=None, limit: int = 50, offset: int = 0):
        captured["args"] = (status, tenant_id, limit, offset)
        return [
            SimpleNamespace(
                id=1,
                topic="cog.some.topic",
                status="pending",
                tenant_id="tenantA",
                dedupe_key="key-1",
                retries=0,
                created_at=None,
                last_error=None,
                payload={"foo": "bar"},
            )
        ]

    monkeypatch.setattr(outbox_db, "list_events_by_status", fake_list)
    resp = await admin_list_outbox(status="pending", tenant="tenantA", limit=10, offset=5)
    assert resp.count == 1
    assert resp.events[0].topic == "cog.some.topic"
    assert captured["args"] == ("pending", "tenantA", 10, 5)


@pytest.mark.asyncio
async def test_admin_outbox_list_invalid_status(monkeypatch):
    def fake_list(*_, **__):
        raise ValueError("bad status")

    monkeypatch.setattr(outbox_db, "list_events_by_status", fake_list)
    with pytest.raises(HTTPException) as exc:
        await admin_list_outbox(status="bogus")
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_admin_outbox_replay(monkeypatch):
    captured = {}

    def fake_replay(event_ids):
        captured["ids"] = list(event_ids)
        return len(event_ids)

    monkeypatch.setattr(outbox_db, "mark_events_for_replay", fake_replay)
    body = S.OutboxReplayRequest(event_ids=[1, 2])
    resp = await admin_replay_outbox(body)
    assert resp.replayed == 2
    assert captured["ids"] == [1, 2]


@pytest.mark.asyncio
async def test_admin_outbox_replay_not_found(monkeypatch):
    monkeypatch.setattr(outbox_db, "mark_events_for_replay", lambda _: 0)
    body = S.OutboxReplayRequest(event_ids=[999])
    with pytest.raises(HTTPException) as exc:
        await admin_replay_outbox(body)
    assert exc.value.status_code == 404
