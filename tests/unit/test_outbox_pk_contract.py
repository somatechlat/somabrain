"""Behavioural contract tests for outbox PK and T-6 durability (ADV C1/C2/C4, F1-F5).

These tests exercise the real functions against a real (sqlite) OutboxEvent
table. ``memsvc.aremember`` / mark-sent are instrumented so call ORDER is
asserted, and the IntegrityError path is driven through the unique
``(tenant_id, dedupe_key)`` constraint — not source greps.

``no_django`` keeps the root conftest from booting the Vault-gated settings
chain; the module fixture configures a minimal Django surface instead.
"""

from __future__ import annotations

import sys
import types
from importlib import util as _ilu
from pathlib import Path

import pytest
from asgiref.sync import sync_to_async

pytestmark = pytest.mark.no_django

ROOT = Path(__file__).resolve().parents[2]


def _bootstrap_minimal_django() -> bool:
    """Configure a minimal Django + sqlite surface for outbox behaviour tests.

    Isolates ``somabrain.settings.resolve`` so importing ``somabrain.db.outbox``
    does not pull the Vault-gated ``settings/__init__`` chain. Only the models
    and helpers these tests actually exercise are loaded.

    Returns True when OutboxEvent is usable.
    """
    from django.conf import settings

    # Always install a Vault-free ``somabrain.settings.resolve``. The real
    # package ``__init__`` enforces the memory-HTTP credential gate and must
    # never be pulled in by these behavioural tests — regardless of which
    # no_django suite won the Django settings race.
    if "somabrain.settings" not in sys.modules or not hasattr(
        sys.modules.get("somabrain.settings"), "__path__"
    ):
        import somabrain  # noqa: F401  — ensure parent package exists

        fake_pkg = types.ModuleType("somabrain.settings")
        fake_pkg.__path__ = [str((ROOT / "somabrain" / "settings").resolve())]
        sys.modules["somabrain.settings"] = fake_pkg
    if "somabrain.settings.resolve" not in sys.modules:
        spec = _ilu.spec_from_file_location(
            "somabrain.settings.resolve",
            str(ROOT / "somabrain" / "settings" / "resolve.py"),
        )
        mod = _ilu.module_from_spec(spec)
        sys.modules["somabrain.settings.resolve"] = mod
        spec.loader.exec_module(mod)

    if settings.configured:
        # Another no_django suite already booted Django. Merge the keys this
        # suite needs; never replace a foreign settings object.
        _gap = {
            "SOMABRAIN_JOURNAL_DIR": "/tmp/somabrain_outbox_pk_journal",
            "SOMABRAIN_JOURNAL_MAX_FILE_SIZE": 1_048_576,
            "JOURNAL_MAX_FILES": 1,
            "JOURNAL_ROTATION_INTERVAL": 3600,
            "JOURNAL_RETENTION_DAYS": 1,
            "JOURNAL_COMPRESSION": False,
            "JOURNAL_SYNC_WRITES": False,
            "SOMABRAIN_DEFAULT_TENANT": "t-contract",
            "SOMABRAIN_NAMESPACE": "public",
            "SOMABRAIN_MEMORY_HTTP_TOKEN": "test-only-token",
            "SOMABRAIN_MEMORY_HTTP_ENDPOINT": "http://127.0.0.1:9",
            "SOMABRAIN_CIRCUIT_FAILURE_THRESHOLD": 3,
            "SOMABRAIN_CIRCUIT_RESET_INTERVAL": 60.0,
            "SOMABRAIN_CIRCUIT_COOLDOWN_INTERVAL": 0.0,
            "SOMABRAIN_MEMORY_MODE": "http",
            "SOMABRAIN_MEMORY_MAX": "1GB",
            "MEMORY_DB_PATH": "/tmp/somabrain_outbox_pk_memory.db",
            "SOMABRAIN_MEMORY_ENABLE_WEIGHTING": False,
            "SOMABRAIN_MEMORY_PHASE_PRIORS": "",
            "SOMABRAIN_MEMORY_QUALITY_EXP": 1.0,
            "SOMABRAIN_MEMORY_DEGRADE_READONLY": False,
            "SOMABRAIN_MEMORY_DEGRADE_TOPIC": "memory.degraded",
            "SOMABRAIN_MEMORY_FAST_ACK": False,
            "SOMABRAIN_EMBED_DIM": 8,
            "SOMABRAIN_EMBEDDER_PROVIDER": "tiny",
        }
        for key, value in _gap.items():
            if not hasattr(settings, key):
                setattr(settings, key, value)
    else:
        settings.configure(
            SECRET_KEY="outbox-pk-contract-tests",
            INSTALLED_APPS=[
                "django.contrib.contenttypes",
                "django.contrib.auth",
                "somabrain.admin.core",
            ],
            DATABASES={
                "default": {
                    "ENGINE": "django.db.backends.sqlite3",
                    "NAME": ":memory:",
                }
            },
            SOMABRAIN_JOURNAL_DIR="/tmp/somabrain_outbox_pk_journal",
            SOMABRAIN_JOURNAL_MAX_FILE_SIZE=1_048_576,
            JOURNAL_MAX_FILES=1,
            JOURNAL_ROTATION_INTERVAL=3600,
            JOURNAL_RETENTION_DAYS=1,
            JOURNAL_COMPRESSION=False,
            JOURNAL_SYNC_WRITES=False,
            ALLOWED_HOSTS=["*"],
            SOMABRAIN_DEFAULT_TENANT="t-contract",
            SOMABRAIN_NAMESPACE="public",
            SOMABRAIN_MEMORY_HTTP_TOKEN="test-only-token",
            SOMABRAIN_MEMORY_HTTP_ENDPOINT="http://127.0.0.1:9",
            SOMABRAIN_CIRCUIT_FAILURE_THRESHOLD=3,
            SOMABRAIN_CIRCUIT_RESET_INTERVAL=60.0,
            SOMABRAIN_CIRCUIT_COOLDOWN_INTERVAL=0.0,
            SOMABRAIN_MEMORY_MODE="http",
            SOMABRAIN_MEMORY_MAX="1GB",
            MEMORY_DB_PATH="/tmp/somabrain_outbox_pk_memory.db",
            SOMABRAIN_MEMORY_ENABLE_WEIGHTING=False,
            SOMABRAIN_MEMORY_PHASE_PRIORS="",
            SOMABRAIN_MEMORY_QUALITY_EXP=1.0,
            SOMABRAIN_MEMORY_DEGRADE_READONLY=False,
            SOMABRAIN_MEMORY_FAST_ACK=False,
            SOMABRAIN_EMBED_DIM=8,
            SOMABRAIN_EMBEDDER_PROVIDER="tiny",
        )
    import django

    try:
        django.setup()
    except Exception:
        return False

    # Another no_django module may have won the settings.configure() race with
    # a surface that does not include our app. Do NOT mutate a foreign
    # settings/app registry — those tests need their own attributes.
    try:
        needed = (
            "django.contrib.contenttypes",
            "django.contrib.auth",
            "somabrain.admin.core",
        )
        installed = list(getattr(settings, "INSTALLED_APPS", []) or [])
        if any(app not in installed for app in needed):
            return False
    except Exception:
        return False

    try:
        from django.db import connection

        connection.creation.create_test_db(verbosity=0)
    except Exception:
        # Tables may already exist from a prior bootstrap in this process.
        pass
    try:
        from somabrain.admin.core.models import OutboxEvent  # noqa: F401
    except Exception:
        return False
    return True


# Configure at import time so pytest-django's test-environment fixture finds a
# configured settings object. Pure-``no_django`` neighbours that also call
# ``settings.configure()`` race at collection; first configurer wins and the
# loser's ORM tests skip (see _require_outbox_db).
_BOOTSTRAP_OK = _bootstrap_minimal_django()


def _require_outbox_db() -> None:
    if not _BOOTSTRAP_OK:
        pytest.skip(
            "Django settings were configured by another no_django module "
            "without somabrain.admin.core; cannot exercise OutboxEvent ORM"
        )


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def outbox_env():
    """Clean OutboxEvent table + instrumented call log."""
    _require_outbox_db()
    from somabrain.admin.core.models import OutboxEvent

    OutboxEvent.objects.all().delete()
    call_log: list[tuple] = []
    yield call_log
    OutboxEvent.objects.all().delete()


@pytest.fixture
def fake_memsvc(outbox_env):
    """Minimal MemoryService stand-in that records ``aremember`` calls."""
    call_log = outbox_env

    class _FakeMemsvc:
        async def aremember(self, key, payload, universe=None):
            call_log.append(("aremember", key))
            return (0.1, 0.2, 0.3)

        async def aremember_bulk(self, items, universe=None):
            for key, _payload in items:
                call_log.append(("aremember", key))
            return [(0.1, 0.2, 0.3)] * len(items)

    return _FakeMemsvc()


# ---------------------------------------------------------------------------
# F1 / IntegrityError path — _durable_accept
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_durable_accept_first_write_is_not_deduplicated(outbox_env):
    from somabrain.api.endpoints.memory_remember import _durable_accept

    event_id, deduplicated, already_sent = await _durable_accept(
        tenant="t-contract",
        key="k1",
        stored_payload={"text": "hello"},
        request_id="r1",
        coord=(1.0, 2.0, 3.0),
    )
    assert isinstance(event_id, int)
    assert deduplicated is False
    assert already_sent is False


@pytest.mark.asyncio
async def test_integrity_error_equal_payload_reports_deduplicated(outbox_env):
    """Collision with IDENTICAL memory content is a replay: ok, deduplicated."""
    from somabrain.admin.core.models import OutboxEvent
    from somabrain.api.endpoints.memory_remember import _durable_accept

    stored = {"text": "hello", "kind": "episodic"}
    first_id, _, _ = await _durable_accept(
        tenant="t-contract",
        key="k1",
        stored_payload=dict(stored),
        request_id="r1",
        coord=(1.0, 2.0, 3.0),
    )
    # Simulate the STORE already acking this row.
    await sync_to_async(
        lambda: OutboxEvent.objects.filter(id=first_id).update(status="sent")
    )()

    second_id, deduplicated, already_sent = await _durable_accept(
        tenant="t-contract",
        key="k1",
        stored_payload=dict(stored),
        request_id="r2",  # request id MUST NOT change identity
        coord=(1.0, 2.0, 3.0),
    )
    assert second_id == first_id
    assert deduplicated is True
    assert already_sent is True


@pytest.mark.asyncio
async def test_integrity_error_equal_payload_pending_still_dedupes(outbox_env):
    from somabrain.api.endpoints.memory_remember import _durable_accept

    stored = {"text": "hello"}
    first_id, _, _ = await _durable_accept(
        tenant="t-contract",
        key="k1",
        stored_payload=dict(stored),
        request_id="r1",
        coord=(1.0, 2.0, 3.0),
    )
    second_id, deduplicated, already_sent = await _durable_accept(
        tenant="t-contract",
        key="k1",
        stored_payload=dict(stored),
        request_id="r2",
        coord=(1.0, 2.0, 3.0),
    )
    assert second_id == first_id
    assert deduplicated is True
    assert already_sent is False  # still pending — not yet in LTM


@pytest.mark.asyncio
async def test_integrity_error_different_payload_refuses_silent_drop(outbox_env):
    """Collision with DIFFERENT content MUST NOT claim durable for the new write."""
    from ninja.errors import HttpError

    from somabrain.api.endpoints.memory_remember import _durable_accept

    await _durable_accept(
        tenant="t-contract",
        key="k1",
        stored_payload={"text": "original"},
        request_id="r1",
        coord=(1.0, 2.0, 3.0),
    )

    with pytest.raises(HttpError) as exc_info:
        await _durable_accept(
            tenant="t-contract",
            key="k1",
            stored_payload={"text": "DIFFERENT"},
            request_id="r2",
            coord=(1.0, 2.0, 3.0),
        )
    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_integrity_error_different_payload_sent_refuses(outbox_env):
    """Sent + different payload is the F1 case: refuse, never ok=durable."""
    from somabrain.admin.core.models import OutboxEvent
    from somabrain.api.endpoints.memory_remember import _durable_accept
    from ninja.errors import HttpError

    first_id, _, _ = await _durable_accept(
        tenant="t-contract",
        key="k1",
        stored_payload={"text": "original"},
        request_id="r1",
        coord=(1.0, 2.0, 3.0),
    )
    await sync_to_async(
        lambda: OutboxEvent.objects.filter(id=first_id).update(status="sent")
    )()

    with pytest.raises(HttpError) as exc_info:
        await _durable_accept(
            tenant="t-contract",
            key="k1",
            stored_payload={"text": "other"},
            request_id="r2",
            coord=(1.0, 2.0, 3.0),
        )
    assert exc_info.value.status_code == 409


# ---------------------------------------------------------------------------
# F3 / T-6 order — store BEFORE mark-sent; failed rows are drained
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_replay_store_precedes_mark_sent(outbox_env, fake_memsvc, monkeypatch):
    """The STORE ack must land before the row is marked sent (T-6)."""
    from somabrain.admin.core.models import OutboxEvent
    from somabrain.api.endpoints.memory_remember import _replay_pending_to_store

    call_log = outbox_env
    await sync_to_async(OutboxEvent.objects.create)(
        topic="memory.store",
        payload={"key": "k1", "payload": {"text": "hello"}, "request_id": "r1"},
        dedupe_key="mem:1.0,2.0,3.0",
        tenant_id="t-contract",
        status="pending",
    )

    import somabrain.db.outbox as outbox_mod

    real_mark_sent = outbox_mod.mark_event_sent

    def _instrumented_mark_sent(event_id):
        call_log.append(("mark_event_sent", event_id))
        return real_mark_sent(event_id)

    monkeypatch.setattr(outbox_mod, "mark_event_sent", _instrumented_mark_sent)

    closed = await _replay_pending_to_store(fake_memsvc, "t-contract")

    assert closed == 1
    assert call_log[0] == ("aremember", "k1"), "store write must come first"
    assert call_log[1][0] == "mark_event_sent", "mark-sent must come after store"
    ev = await sync_to_async(
        lambda: OutboxEvent.objects.get(dedupe_key="mem:1.0,2.0,3.0")
    )()
    assert ev.status == "sent"


@pytest.mark.asyncio
async def test_replay_never_marks_sent_when_store_fails(outbox_env, monkeypatch):
    from somabrain.admin.core.models import OutboxEvent
    from somabrain.api.endpoints.memory_remember import _replay_pending_to_store

    call_log = outbox_env
    await sync_to_async(OutboxEvent.objects.create)(
        topic="memory.store",
        payload={"key": "k1", "payload": {"text": "hello"}, "request_id": "r1"},
        dedupe_key="mem:1.0,2.0,3.0",
        tenant_id="t-contract",
        status="pending",
    )

    class _Boom:
        async def aremember(self, key, payload, universe=None):
            call_log.append(("aremember", key))
            raise RuntimeError("store down")

    import somabrain.db.outbox as outbox_mod

    def _must_not_mark(event_id):
        call_log.append(("mark_event_sent", event_id))
        raise AssertionError("mark_event_sent must not run when the store fails")

    monkeypatch.setattr(outbox_mod, "mark_event_sent", _must_not_mark)

    closed = await _replay_pending_to_store(_Boom(), "t-contract")
    assert closed == 0
    assert ("mark_event_sent", 1) not in call_log
    ev = await sync_to_async(
        lambda: OutboxEvent.objects.get(dedupe_key="mem:1.0,2.0,3.0")
    )()
    assert ev.status == "pending"


@pytest.mark.asyncio
async def test_replay_picks_up_failed_rows(outbox_env, fake_memsvc):
    """F3: a ``failed`` row is not a dead end — the drain retries it."""
    from somabrain.admin.core.models import OutboxEvent
    from somabrain.api.endpoints.memory_remember import _replay_pending_to_store

    ev = await sync_to_async(OutboxEvent.objects.create)(
        topic="memory.store",
        payload={"key": "k9", "payload": {"text": "retry-me"}, "request_id": "r9"},
        dedupe_key="mem:9.0,9.0,9.0",
        tenant_id="t-contract",
        status="failed",
        retries=5,
        last_error="previous failure",
    )
    assert ev.status == "failed"

    closed = await _replay_pending_to_store(fake_memsvc, "t-contract")
    assert closed == 1

    def _reload():
        ev.refresh_from_db()
        return ev.status

    status = await sync_to_async(_reload)()
    assert status == "sent"


def test_get_pending_events_by_tenant_batch_includes_failed(outbox_env):
    from somabrain.admin.core.models import OutboxEvent
    from somabrain.db.outbox import get_pending_events_by_tenant_batch

    OutboxEvent.objects.create(
        topic="memory.store",
        payload={"key": "k-fail", "payload": {"text": "x"}},
        dedupe_key="mem:0.0,0.0,0.0",
        tenant_id="t-contract",
        status="failed",
    )
    batches = get_pending_events_by_tenant_batch()
    ids = {e.id for e in batches.get("t-contract", [])}
    assert len(ids) == 1


def test_mark_events_for_replay_resets_failed(outbox_env):
    from somabrain.admin.core.models import OutboxEvent
    from somabrain.db.outbox import mark_event_failed, mark_events_for_replay

    ev = OutboxEvent.objects.create(
        topic="memory.store",
        payload={"key": "k1", "payload": {"text": "x"}},
        dedupe_key="mem:1.0,1.0,1.0",
        tenant_id="t-contract",
        status="pending",
    )
    mark_event_failed(ev.id, "boom")
    ev.refresh_from_db()
    assert ev.status == "failed"

    n = mark_events_for_replay([ev.id])
    assert n == 1
    ev.refresh_from_db()
    assert ev.status == "pending"
    assert ev.retries == 0


# ---------------------------------------------------------------------------
# PK / idempotency-key contracts (behavioural)
# ---------------------------------------------------------------------------


def test_enqueue_memory_event_returns_int_pk(outbox_env):
    from somabrain.db.outbox import enqueue_memory_event

    event_id = enqueue_memory_event(
        topic="memory.store",
        payload={"key": "k1", "payload": {"text": "hello"}},
        tenant_id="t-contract",
        coord=(1.0, 2.0, 3.0),
        extra_key=None,
        check_backpressure_flag=True,
    )
    assert isinstance(event_id, int)
    assert event_id > 0


def test_enqueue_event_rejects_missing_dedupe_key(outbox_env):
    import pytest as _pytest

    from somabrain.db.outbox import enqueue_event

    with _pytest.raises(ValueError, match="dedupe_key"):
        enqueue_event(
            topic="memory.store",
            payload={"x": 1},
            dedupe_key=None,
            tenant_id="t-contract",
        )
    with _pytest.raises(ValueError, match="dedupe_key"):
        enqueue_event(
            topic="memory.store",
            payload={"x": 1},
            dedupe_key="  ",
            tenant_id="t-contract",
        )


def test_idempotency_key_is_mem_coord_only():
    _require_outbox_db()
    from somabrain.db.outbox import _idempotency_key

    key = _idempotency_key("memory.store", (1.0, 2.0, 3.0), "tenant-x", "req-999")
    assert key == "mem:1.0,2.0,3.0"
    # request id / operation / tenant MUST NOT leak into the key
    assert "req-999" not in key
    assert "memory.store" not in key
    assert "tenant-x" not in key


def test_idempotency_key_fails_closed_without_coord():
    _require_outbox_db()
    import pytest as _pytest

    from somabrain.db.outbox import _idempotency_key

    with _pytest.raises(ValueError):
        _idempotency_key("memory.store", None, "t", None)


# ---------------------------------------------------------------------------
# F2 — _record_to_outbox fails closed (no silent None)
# ---------------------------------------------------------------------------


def test_record_to_outbox_fail_closed_on_enqueue_error(outbox_env, monkeypatch):
    import pytest as _pytest

    import somabrain.db.outbox as outbox_mod
    from somabrain.memory.remember import _record_to_outbox

    def _boom(**kwargs):
        raise RuntimeError("db down")

    monkeypatch.setattr(outbox_mod, "enqueue_memory_event", _boom)

    with _pytest.raises(RuntimeError, match="db down"):
        _record_to_outbox(
            (1.0, 2.0, 3.0), {"text": "hello"}, "t-contract", "r1"
        )


def test_record_to_outbox_fail_closed_on_backpressure(outbox_env, monkeypatch):
    """Backpressure MUST raise — returning None drops the durable trail (F2)."""
    import pytest as _pytest

    import somabrain.db.outbox as outbox_mod
    from somabrain.memory.remember import _record_to_outbox

    def _backpressure(**kwargs):
        raise outbox_mod.OutboxBackpressureError(pending_count=10_001)

    monkeypatch.setattr(outbox_mod, "enqueue_memory_event", _backpressure)

    with _pytest.raises(outbox_mod.OutboxBackpressureError):
        _record_to_outbox(
            (1.0, 2.0, 3.0), {"text": "hello"}, "t-contract", "r1"
        )


def test_record_to_outbox_returns_pk_on_success(outbox_env):
    from somabrain.memory.remember import _record_to_outbox

    event_id = _record_to_outbox(
        (1.0, 2.0, 3.0), {"text": "hello"}, "t-contract", "r1"
    )
    assert isinstance(event_id, int)


# ---------------------------------------------------------------------------
# F5 — response flags reflect real state
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_already_sent_replay_skips_requeue(outbox_env, fake_memsvc):
    """A sent+equal collision must report queued_for_ltm=False, not re-queue."""
    from somabrain.admin.core.models import OutboxEvent
    from somabrain.api.endpoints.memory_remember import _durable_accept

    stored = {"text": "hello"}
    first_id, _, _ = await _durable_accept(
        tenant="t-contract",
        key="k1",
        stored_payload=dict(stored),
        request_id="r1",
        coord=(1.0, 2.0, 3.0),
    )
    await sync_to_async(
        lambda: OutboxEvent.objects.filter(id=first_id).update(status="sent")
    )()

    _second_id, deduplicated, already_sent = await _durable_accept(
        tenant="t-contract",
        key="k1",
        stored_payload=dict(stored),
        request_id="r2",
        coord=(1.0, 2.0, 3.0),
    )
    # The endpoint uses ``already_sent`` to set queued_for_ltm=False and
    # durability=persisted_ltm without a new hop.
    assert already_sent is True
    assert deduplicated is True
    # Only one row exists for this coord — no multiplier.
    count = await sync_to_async(
        lambda: OutboxEvent.objects.filter(tenant_id="t-contract").count()
    )()
    assert count == 1


# ---------------------------------------------------------------------------
# Publisher drain: agent-path rows (coord, no key) still write to the store
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_replay_accepts_agent_coord_payload(outbox_env, fake_memsvc):
    from somabrain.admin.core.models import OutboxEvent
    from somabrain.api.endpoints.memory_remember import _replay_pending_to_store

    call_log = outbox_env
    await sync_to_async(OutboxEvent.objects.create)(
        topic="memory.store",
        # Agent path (memory/remember.py) stores ``coord`` not ``key``.
        payload={"coord": [4.0, 5.0, 6.0], "payload": {"text": "agent"}},
        dedupe_key="mem:4.0,5.0,6.0",
        tenant_id="t-contract",
        status="pending",
    )

    closed = await _replay_pending_to_store(fake_memsvc, "t-contract")
    assert closed == 1
    assert call_log[0] == ("aremember", "4.0,5.0,6.0")
    ev = await sync_to_async(
        lambda: OutboxEvent.objects.get(dedupe_key="mem:4.0,5.0,6.0")
    )()
    assert ev.status == "sent"


# ---------------------------------------------------------------------------
# T-6 order — agent persist path: outbox BEFORE store, mark-sent AFTER ack
# ---------------------------------------------------------------------------


def test_remember_sync_persist_outbox_before_store_mark_after(outbox_env, monkeypatch):
    """E2.1/E2.2 behavioural order on the agent persist path.

    Spy the outbox enqueue, the store hop, and mark-sent. The call log must
    be exactly ``enqueue → store → mark_sent`` — never mark-sent before the
    store ack, never store before the durable row exists.
    """
    import somabrain.db.outbox as outbox_mod
    from somabrain.memory.remember import remember_sync_persist

    call_log = outbox_env

    real_enqueue = outbox_mod.enqueue_memory_event

    def _spy_enqueue(*args, **kwargs):
        call_log.append(("outbox_write",))
        return real_enqueue(*args, **kwargs)

    def _spy_store(body, headers):
        call_log.append(("store",))
        return True, {"coordinate": [1.0, 2.0, 3.0]}

    real_mark = outbox_mod.mark_event_sent

    def _spy_mark(event_id):
        call_log.append(("mark_event_sent", event_id))
        return real_mark(event_id)

    monkeypatch.setattr(outbox_mod, "enqueue_memory_event", _spy_enqueue)
    monkeypatch.setattr(outbox_mod, "mark_event_sent", _spy_mark)

    class _Transport:
        client = object()
        async_client = None

    class _Cfg:
        tenant = "t-contract"
        namespace = "public"

    remember_sync_persist(
        _Transport(),
        _Cfg(),
        "k-sync",
        {"text": "hello"},
        "r-sync",
        _spy_store,
    )

    assert [c[0] for c in call_log] == ["outbox_write", "store", "mark_event_sent"]


@pytest.mark.asyncio
async def test_persist_ltm_background_aremember_before_mark_sent(
    outbox_env, fake_memsvc, monkeypatch
):
    """Background LTM path (fast-ack): store ack lands before mark-sent (T-6)."""
    from somabrain.api.endpoints.memory_remember import _persist_ltm_in_background
    from somabrain.admin.core.models import OutboxEvent

    call_log = outbox_env
    ev = await sync_to_async(OutboxEvent.objects.create)(
        topic="memory.store",
        payload={"key": "k1", "payload": {"text": "hello"}},
        dedupe_key="mem:1.0,2.0,3.0",
        tenant_id="t-contract",
        status="pending",
    )
    import somabrain.db.outbox as outbox_mod

    real_mark = outbox_mod.mark_event_sent

    def _spy_mark(event_id):
        call_log.append(("mark_event_sent", event_id))
        return real_mark(event_id)

    monkeypatch.setattr(outbox_mod, "mark_event_sent", _spy_mark)

    await _persist_ltm_in_background(
        fake_memsvc, "k1", {"text": "hello"}, "r1", ev.id, "t-contract"
    )
    assert call_log[0] == ("aremember", "k1")
    assert call_log[1][0] == "mark_event_sent"

    def _reload():
        ev.refresh_from_db()
        return ev.status

    assert await sync_to_async(_reload)() == "sent"


@pytest.mark.asyncio
async def test_persist_ltm_background_failure_leaves_pending(outbox_env, monkeypatch):
    from somabrain.admin.core.models import OutboxEvent
    from somabrain.api.endpoints.memory_remember import _persist_ltm_in_background

    call_log = outbox_env
    ev = await sync_to_async(OutboxEvent.objects.create)(
        topic="memory.store",
        payload={"key": "k1", "payload": {"text": "hello"}},
        dedupe_key="mem:1.0,2.0,3.0",
        tenant_id="t-contract",
        status="pending",
    )
    import somabrain.db.outbox as outbox_mod

    def _must_not_mark(event_id):
        call_log.append(("mark_event_sent", event_id))
        raise AssertionError("mark_event_sent must not run when the store fails")

    monkeypatch.setattr(outbox_mod, "mark_event_sent", _must_not_mark)

    class _Boom:
        async def aremember(self, key, payload, universe=None):
            call_log.append(("aremember", key))
            raise RuntimeError("store down")

    await _persist_ltm_in_background(_Boom(), "k1", {"text": "x"}, "r1", ev.id, "t-contract")
    assert ("mark_event_sent", ev.id) not in call_log

    def _reload():
        ev.refresh_from_db()
        return ev.status

    assert await sync_to_async(_reload)() == "pending"


# ---------------------------------------------------------------------------
# Response flags (F5) — queued_for_ltm / deduplicated / durability match reality
# ---------------------------------------------------------------------------


class _EndpointSpyMemsvc:
    """Minimal MemoryService stand-in for driving ``remember_memory_async``."""

    def __init__(self, call_log, *, circuit_open=False, fail=False):
        self._log = call_log
        self._circuit_open = circuit_open
        self._fail = fail

    def _reset_circuit_if_needed(self):
        return False

    def _is_circuit_open(self):
        return self._circuit_open

    def client(self):
        outer = self

        class _C:
            def coord_for_key(self, key, universe=None):
                outer._log.append(("coord_for_key", key, universe))
                # Unique coord per (key, universe) so batch items do not
                # collide on the mem:{coord} dedupe key.
                return (float(abs(hash((key, universe))) % 97) + 1.0, 2.0, 3.0)

        return _C()

    async def aremember(self, key, payload, universe=None):
        if self._circuit_open:
            from somabrain.core.exceptions import CircuitBreakerOpen

            raise CircuitBreakerOpen("Memory service unavailable (circuit open)")
        self._log.append(("aremember", key))
        if self._fail:
            raise RuntimeError("store down")
        return (1.0, 2.0, 3.0)

    async def aremember_bulk(self, items, universe=None):
        if self._circuit_open:
            from somabrain.core.exceptions import CircuitBreakerOpen

            raise CircuitBreakerOpen("Memory service unavailable (circuit open)")
        items = list(items)
        for key, payload in items:
            self._log.append(("aremember_bulk", key, payload.get("universe"), universe))
        return [(1.0, 2.0, 3.0)] * len(items)


class _FakeRequest:
    def __init__(self, tenant="t-contract"):
        self.auth = {"tenant_id": tenant}
        self.headers = {}


def _stub_remember_endpoint(monkeypatch, memsvc, call_log):
    from somabrain.api.endpoints import memory_remember as mr

    monkeypatch.setattr(mr, "require_auth", lambda *a, **k: None)
    monkeypatch.setattr(mr, "_get_memory_pool", lambda: object())
    monkeypatch.setattr(mr, "_get_wm", lambda: None)
    monkeypatch.setattr(
        mr,
        "_get_embedder",
        lambda: type("E", (), {"embed": staticmethod(lambda t: [0.0])})(),
    )
    monkeypatch.setattr(mr, "ensure_embedding_dim", lambda emb, **k: emb)
    monkeypatch.setattr(mr, "_resolve_namespace", lambda t, n: "public")
    monkeypatch.setattr(mr, "MemoryService", lambda pool, ns: memsvc)

    import somabrain.tenant as tenant_mod

    monkeypatch.setattr(
        tenant_mod,
        "get_tenant_sync",
        lambda request, namespace: tenant_mod.TenantContext(
            tenant_id="t-contract", namespace="public"
        ),
    )

    import somabrain.db.outbox as outbox_mod

    real_mark = outbox_mod.mark_event_sent

    def _spy_mark(event_id):
        call_log.append(("mark_event_sent", event_id))
        return real_mark(event_id)

    monkeypatch.setattr(outbox_mod, "mark_event_sent", _spy_mark)
    return mr


@pytest.mark.asyncio
async def test_remember_response_flags_after_store_ack(outbox_env, monkeypatch):
    """Successful sync write: durability/queued/dedup reflect the real hop."""
    from somabrain.api.memory.models import (
        MemoryDurability,
        MemoryWriteRequest,
    )

    call_log = outbox_env
    memsvc = _EndpointSpyMemsvc(call_log)
    mr = _stub_remember_endpoint(monkeypatch, memsvc, call_log)

    payload = MemoryWriteRequest(
        tenant="t-contract",
        namespace="public",
        key="k-flags",
        value={"text": "hello"},
    )
    resp = await mr.remember_memory_async(_FakeRequest(), payload)

    assert resp["ok"] is True
    assert resp["deduplicated"] is False
    assert resp["queued_for_ltm"] is False
    assert resp["persisted_to_ltm"] is True
    assert resp["durability"] == MemoryDurability.PERSISTED_LTM
    names = [c[0] for c in call_log]
    assert names.index("aremember") < names.index("mark_event_sent")


@pytest.mark.asyncio
async def test_remember_response_flags_on_circuit_open(outbox_env, monkeypatch):
    """Store down: durable outbox only — never claim persisted_to_ltm."""
    from somabrain.api.memory.models import MemoryDurability, MemoryWriteRequest

    call_log = outbox_env
    memsvc = _EndpointSpyMemsvc(call_log, circuit_open=True)
    mr = _stub_remember_endpoint(monkeypatch, memsvc, call_log)

    payload = MemoryWriteRequest(
        tenant="t-contract",
        namespace="public",
        key="k-down",
        value={"text": "hello"},
    )
    resp = await mr.remember_memory_async(_FakeRequest(), payload)

    assert resp["ok"] is True
    assert resp["persisted_to_ltm"] is False
    assert resp["queued_for_ltm"] is True
    assert resp["durability"] == MemoryDurability.DURABLE_OUTBOX
    assert resp["deduplicated"] is False
    assert ("aremember", "k-down") not in call_log
    assert ("mark_event_sent", resp["outbox_event_id"]) not in call_log


@pytest.mark.asyncio
async def test_remember_response_flags_on_idempotent_replay(outbox_env, monkeypatch):
    """Sent+equal collision: deduplicated=True, queued_for_ltm=False, no re-hop."""
    from somabrain.admin.core.models import OutboxEvent
    from somabrain.api.memory.models import MemoryDurability, MemoryWriteRequest

    call_log = outbox_env
    memsvc = _EndpointSpyMemsvc(call_log)
    mr = _stub_remember_endpoint(monkeypatch, memsvc, call_log)

    payload = MemoryWriteRequest(
        tenant="t-contract",
        namespace="public",
        key="k-replay",
        value={"text": "same"},
    )
    first = await mr.remember_memory_async(_FakeRequest(), payload)
    assert first["deduplicated"] is False
    assert first["persisted_to_ltm"] is True

    # Close the row as the store already acked it.
    await sync_to_async(
        lambda: OutboxEvent.objects.filter(id=first["outbox_event_id"]).update(
            status="sent"
        )
    )()

    second = await mr.remember_memory_async(_FakeRequest(), payload)
    assert second["deduplicated"] is True
    assert second["queued_for_ltm"] is False
    assert second["persisted_to_ltm"] is True
    assert second["durability"] == MemoryDurability.PERSISTED_LTM
    # No second store hop for a pure replay.
    assert call_log.count(("aremember", "k-replay")) == 1


# ---------------------------------------------------------------------------
# Forget — delete coord → not in recall (behavioural store, no HTTP)
# ---------------------------------------------------------------------------


class _MemClient:
    """In-memory client with the ops the forget/recall seam uses."""

    def __init__(self, store: dict):
        self.store = store

    def coord_for_key(self, key, universe=None):
        return (float(abs(hash(key)) % 7), 1.0, 2.0)

    def remember(self, key, payload, universe=None):
        coord = self.coord_for_key(key, universe)
        self.store[coord] = dict(payload or {})
        return coord

    async def aremember(self, key, payload, universe=None):
        return self.remember(key, payload, universe)

    def delete(self, coordinate):
        coord = tuple(float(x) for x in coordinate)
        return self.store.pop(coord, None) is not None

    async def adelete(self, coordinate):
        return self.delete(coordinate)

    def recall(self, query, top_k=3, universe=None, embedding=None):
        hits = []
        for coord, payload in self.store.items():
            if universe and str(payload.get("universe") or "real") != str(universe):
                continue
            hits.append({"coord": coord, "payload": payload, "score": 1.0})
        return hits[:top_k]

    async def arecall(self, query, top_k=3, universe=None, embedding=None):
        return self.recall(query, top_k=top_k, universe=universe, embedding=embedding)

    def fetch_by_coord(self, coord, universe=None):
        return self.store.get(tuple(float(x) for x in coord))


class _MemBackend:
    def __init__(self):
        self._spaces: dict[str, dict] = {}

    def for_namespace(self, namespace):
        return _MemClient(self._spaces.setdefault(namespace or "", {}))


@pytest.mark.asyncio
async def test_forget_delete_coord_not_in_recall():
    """Forget removes the coord: a later recall must not resurrect it."""
    from somabrain.services.memory_service import MemoryService

    backend = _MemBackend()
    svc = MemoryService(backend, "public")

    coord = await svc.aremember("k-forget", {"text": "secret", "universe": "real"})
    hits = await svc.arecall("secret", universe="real")
    assert hits, "remember must land before forget"

    deleted = await svc.adelete(coord)
    assert deleted is True

    after = await svc.arecall("secret", universe="real")
    assert after == [], "forgotten coord must not appear in recall"
    assert svc.fetch_by_coord(coord) is None


@pytest.mark.asyncio
async def test_forget_endpoint_removes_coord_from_recall(outbox_env, monkeypatch):
    """Drive the real /forget handler against the in-memory store."""
    from somabrain.api.endpoints import memory as mem_api
    from somabrain.api.memory.models import ForgetRequest
    from somabrain.services.memory_service import MemoryService
    from somabrain.tenant import TenantContext

    backend = _MemBackend()
    svc = MemoryService(backend, "public")
    coord = await svc.aremember("k-forget-api", {"text": "gone", "universe": "real"})

    async def _tenant(request, namespace):
        return TenantContext(tenant_id="t-contract", namespace="public")

    monkeypatch.setattr(mem_api, "get_tenant", _tenant)
    monkeypatch.setattr(mem_api, "require_auth", lambda *a, **k: None)
    monkeypatch.setattr(mem_api, "_get_memory_pool", lambda: backend)
    monkeypatch.setattr(mem_api, "_get_wm", lambda: None)
    monkeypatch.setattr(mem_api, "_resolve_namespace", lambda t, n: "public")
    monkeypatch.setattr(mem_api, "MemoryService", lambda pool, ns: svc)

    resp = await mem_api.forget_memory(
        _FakeRequest(),
        ForgetRequest(coord=list(coord), tenant="t-contract"),
    )
    assert resp["ok"] is True
    after = await svc.arecall("gone", universe="real")
    assert after == []


# ---------------------------------------------------------------------------
# Batch path honours universe (ADV A2)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_batch_path_honours_per_item_universe(outbox_env, monkeypatch):
    """Item universe wins over the batch default for coord identity (ADV A2)."""
    from somabrain.api.memory.models import (
        MemoryBatchWriteItem,
        MemoryBatchWriteRequest,
        MemoryWriteRequest,  # noqa: F401  — import surface check
    )

    call_log = outbox_env
    memsvc = _EndpointSpyMemsvc(call_log)
    mr = _stub_remember_endpoint(monkeypatch, memsvc, call_log)

    payload = MemoryBatchWriteRequest(
        tenant="t-contract",
        namespace="public",
        universe="real",
        items=[
            MemoryBatchWriteItem(key="k-batch-a", value={"text": "a"}, universe="alt"),
            MemoryBatchWriteItem(key="k-batch-b", value={"text": "b"}),
        ],
    )
    resp = await mr.remember_memory_batch(_FakeRequest(), payload)

    assert resp["ok"] is True
    coord_calls = [c for c in call_log if c[0] == "coord_for_key"]
    assert ("coord_for_key", "k-batch-a", "alt") in coord_calls
    assert ("coord_for_key", "k-batch-b", "real") in coord_calls
    # Bulk hop carries per-item universe on the body.
    bulk = [c for c in call_log if c[0] == "aremember_bulk"]
    assert bulk, "batch must hit the store"
    by_key = {row[1]: row[2] for row in bulk}
    assert by_key["k-batch-a"] == "alt"
    assert by_key["k-batch-b"] == "real"
    # Result flags are real (not hardcoded): first write is not deduplicated.
    assert all(r["deduplicated"] is False for r in resp["results"])
    assert all(r["queued_for_ltm"] is False for r in resp["results"])
    assert all(r["persisted_to_ltm"] is True for r in resp["results"])
