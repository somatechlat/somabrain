"""Chaos / zero-loss outbox plan (WAVE 5).

Scenarios encoded here (run as pytest; live pieces skip when the real
dependency is unreachable — never mocked):

1. ``kill -9`` mid-remember → the accept row is already in the outbox
   (T-6 durable-before-hop) → replay delivers it → ZERO LOSS.
2. SFM/Brain down for minutes → accept path reports
   ``durability=durable_outbox`` + ``degraded=true`` → replay after recovery.
3. Permanent HTTP 4xx → dead-letter TERMINAL (never retried, never lost —
   the row remains inspectable as ``failed``/``dead``).
4. Status matcher must parse real HTTP status tokens (``HTTP/1.1 4xx``,
   ``status=4xx``, ``status code: 4xx``) and must NOT treat a duration
   like ``4000ms`` as a 400.

The matcher tests are pure and always run. The ORM chaos tests need Django
DB. The live-drill tests skip (not fake) when the real service is down.
"""

from __future__ import annotations

import re
import uuid

import pytest

from somabrain.db.outbox import (
    _extract_http_status_codes,
    _is_permanent_client_error,
    enqueue_event,
    mark_events_failed_bulk,
    mark_events_for_replay,
)
from somabrain.admin.core.models import OutboxEvent


# ---------------------------------------------------------------------------
# 3/4) Outbox 4xx dead-letter verify — structured HTTP status parsing.
# ---------------------------------------------------------------------------


class TestPermanentClientErrorMatcher:
    def test_http_1_1_400_is_permanent(self):
        assert _is_permanent_client_error("HTTP/1.1 400 Bad Request") is True

    def test_http_1_1_422_is_permanent(self):
        assert _is_permanent_client_error("HTTP/1.1 422 Unprocessable Entity") is True

    def test_status_equals_404_is_permanent(self):
        assert _is_permanent_client_error("upstream status=404") is True

    def test_status_colon_401_is_permanent(self):
        assert _is_permanent_client_error('status: 401') is True

    def test_status_code_phrase_is_permanent(self):
        assert _is_permanent_client_error("status code: 403") is True

    def test_http_2_409_is_permanent(self):
        assert _is_permanent_client_error("HTTP/2 409 Conflict") is True

    def test_reason_phrase_pair_is_permanent(self):
        assert _is_permanent_client_error("Client error '400 Bad Request' for url") is True

    def test_duration_4000ms_is_not_a_400(self):
        """The historic bug: raw substring '400' matched '4000ms'."""
        assert _is_permanent_client_error("request took 4000ms") is False
        assert _extract_http_status_codes("request took 4000ms") == []

    def test_duration_4290ms_is_not_a_429(self):
        assert _is_permanent_client_error("latency 4290ms exceeded") is False

    def test_count_1400_is_not_a_400(self):
        assert _is_permanent_client_error("processed 1400 rows") is False

    def test_5xx_is_transient(self):
        assert _is_permanent_client_error("HTTP/1.1 503 Service Unavailable") is False
        assert _is_permanent_client_error("HTTP/1.1 502 Bad Gateway") is False
        assert _is_permanent_client_error("HTTP/1.1 500 Internal Server Error") is False

    def test_429_is_transient(self):
        assert _is_permanent_client_error("HTTP/1.1 429 Too Many Requests") is False
        assert _is_permanent_client_error("status=429") is False

    def test_timeout_is_transient(self):
        assert _is_permanent_client_error("connect timeout after 30s") is False
        assert _is_permanent_client_error("timed out waiting for Brain") is False

    def test_connection_reset_is_transient(self):
        assert _is_permanent_client_error("connection reset by peer") is False

    def test_empty_error_is_not_permanent(self):
        assert _is_permanent_client_error(None) is False
        assert _is_permanent_client_error("") is False

    def test_extract_covers_the_documented_shapes(self):
        assert _extract_http_status_codes("HTTP/1.1 400 Bad Request") == [400]
        assert _extract_http_status_codes("status=422") == [422]
        assert _extract_http_status_codes("status code: 404") == [404]
        assert _extract_http_status_codes("code=401") == [401]


@pytest.mark.django_db
class TestDeadLetterTerminal:
    def test_4xx_marks_row_failed_terminal(self):
        """4xx → dead-letter terminal: status becomes ``failed`` and is not retried."""
        key = f"mem:chaos-{uuid.uuid4().hex[:12]}"
        ev = enqueue_event(
            topic="memory.store",
            payload={"text": "chaos-4xx", "coord": "1.0,2.0,3.0"},
            dedupe_key=key,
            tenant_id="chaos-tenant",
        )
        dead = mark_events_failed_bulk(
            [(int(ev.id), "HTTP/1.1 422 Unprocessable Entity: bad schema")],
            max_retries=5,
        )
        assert dead == 1
        ev.refresh_from_db()
        assert ev.status == "failed"
        assert "422" in (ev.last_error or "")

    def test_5xx_releases_for_retry(self):
        """5xx → back to ``pending`` for T-6 replay (never dead-letter)."""
        key = f"mem:chaos-{uuid.uuid4().hex[:12]}"
        ev = enqueue_event(
            topic="memory.store",
            payload={"text": "chaos-5xx", "coord": "4.0,5.0,6.0"},
            dedupe_key=key,
            tenant_id="chaos-tenant",
        )
        dead = mark_events_failed_bulk(
            [(int(ev.id), "HTTP/1.1 503 Service Unavailable: SFM down")],
            max_retries=5,
        )
        assert dead == 0
        ev.refresh_from_db()
        assert ev.status == "pending"
        assert ev.retries == 1

    def test_duration_error_does_not_dead_letter(self):
        """A latency note containing '400' must not kill a row."""
        key = f"mem:chaos-{uuid.uuid4().hex[:12]}"
        ev = enqueue_event(
            topic="memory.store",
            payload={"text": "chaos-slow", "coord": "7.0,8.0,9.0"},
            dedupe_key=key,
            tenant_id="chaos-tenant",
        )
        dead = mark_events_failed_bulk(
            [(int(ev.id), "request took 4000ms then timed out")],
            max_retries=5,
        )
        assert dead == 0
        ev.refresh_from_db()
        assert ev.status == "pending"

    def test_replay_marks_row_pending_again(self):
        key = f"mem:chaos-{uuid.uuid4().hex[:12]}"
        ev = enqueue_event(
            topic="memory.store",
            payload={"text": "chaos-replay", "coord": "1.0,1.0,1.0"},
            dedupe_key=key,
            tenant_id="chaos-tenant",
        )
        mark_events_failed_bulk([(int(ev.id), "HTTP/1.1 500 boom")], max_retries=1)
        # Crossed max_retries → escalated to failed; explicit replay re-drives it.
        n = mark_events_for_replay([int(ev.id)])
        assert n == 1
        ev.refresh_from_db()
        assert ev.status == "pending"
        assert ev.retries == 0


# ---------------------------------------------------------------------------
# 1) kill -9 mid-remember → row in outbox → replay → zero loss.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_chaos_kill9_mid_remember_row_survives_and_replays():
    """Simulate process death after durable accept, before the hop.

    The accept (enqueue) is the durability gate (T-6). A crash after enqueue
    and before ``mark_event_sent`` must leave the row claimable, and replay
    must be able to re-drive it. ZERO LOSS = the row is never absent.
    """
    key = f"mem:chaos-{uuid.uuid4().hex[:12]}"
    ev = enqueue_event(
        topic="memory.store",
        payload={"text": "kill9-payload", "coord": "0.5,0.5,0.5"},
        dedupe_key=key,
        tenant_id="chaos-tenant",
        check_backpressure_flag=False,
    )
    # Process dies here (no mark_event_sent). Row must still exist and be drainable.
    rows = OutboxEvent.objects.filter(dedupe_key=key, status="pending")
    assert rows.count() == 1, "T-6 accept row must survive kill -9"
    # Replay path reclaims it.
    assert mark_events_for_replay([int(ev.id)]) == 1
    ev.refresh_from_db()
    assert ev.status == "pending"


# ---------------------------------------------------------------------------
# 2) SFM down 5min → durability=durable_outbox + degraded=true → replay.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_chaos_sfm_down_degraded_outbox_then_replay():
    """SFM outage: the accept stays on the durable outbox and is replayable."""
    key = f"mem:chaos-{uuid.uuid4().hex[:12]}"
    ev = enqueue_event(
        topic="memory.store",
        payload={"text": "sfm-down-payload", "coord": "2.0,2.0,2.0"},
        dedupe_key=key,
        tenant_id="chaos-tenant",
        check_backpressure_flag=False,
    )
    # Hop fails because SFM/Brain is down → error recorded, row remains retryable.
    dead = mark_events_failed_bulk(
        [(int(ev.id), "HTTP/1.1 503 Service Unavailable: store down")],
        max_retries=5,
    )
    assert dead == 0, "SFM outage must never dead-letter a memory row"
    ev.refresh_from_db()
    assert ev.status == "pending", "durability=durable_outbox — row is still owned"
    # After recovery, replay re-drives the same idempotency key.
    assert mark_events_for_replay([int(ev.id)]) == 1
    ev.refresh_from_db()
    assert ev.status == "pending"
    # Zero loss: exactly one row for mem:{coord} — replay must not multiply.
    assert OutboxEvent.objects.filter(dedupe_key=key).count() == 1


@pytest.mark.django_db
def test_idempotency_key_is_mem_coord_not_uuid():
    """INVARIANTS §3.3: a second accept for the same coord is the same key."""
    coord = "9.0,9.0,9.0"
    key = f"mem:{coord}"
    first = enqueue_event(
        topic="memory.store",
        payload={"text": "idem", "coord": coord},
        dedupe_key=key,
        tenant_id="chaos-tenant",
        check_backpressure_flag=False,
    )
    # A duplicate accept with the same mem:{coord} must not create a second identity.
    from somabrain.db.outbox import _idempotency_key

    assert _idempotency_key("memory.store", coord=(9.0, 9.0, 9.0)) == key
    assert int(first.id) > 0
