"""B17: honour the SFM ``degraded`` flag — never a silent empty recall.

SFM's ``MemorySearchResponse`` carries ``degraded: bool`` (stack lock). When
the vector path fails and SFM falls back, it answers ``degraded=true``. A
client that ignores that flag and returns ``[]`` dresses a partial/unavailable
store as "no history" (B17). These tests pin the contract:

* ``degraded=true`` + no hits  → ``MemoryRecallUnavailable`` (fail-closed)
* ``degraded=true`` + hits     → hits are returned but each carries
  ``hit.degraded is True`` so callers can see the flag
* ``degraded=false`` / absent  → ordinary success, genuine empty stays ``[]``
"""

from __future__ import annotations

import pytest

from somabrain.memory.hit_processing import normalize_recall_hits
from somabrain.memory.recall_ops import (
    MemoryRecallUnavailable,
    process_search_response,
)
from somabrain.memory.types import RecallHit

pytestmark = pytest.mark.no_django


def _rescore(hits, query_text):
    return hits


def _hit_payload(task: str) -> dict:
    return {"task": task, "tenant": "tenant-degraded", "universe": "real"}


# ---------------------------------------------------------------------------
# RecallHit carries the flag
# ---------------------------------------------------------------------------


def test_recall_hit_exposes_degraded_flag_default_false() -> None:
    hit = RecallHit(payload={"task": "x"}, score=1.0)
    assert hit.degraded is False


# ---------------------------------------------------------------------------
# process_search_response honours degraded=true
# ---------------------------------------------------------------------------


def test_degraded_true_empty_response_raises_not_silent_empty() -> None:
    """degraded=true with no hits is an outage — never a successful []."""
    data = {"hits": [], "degraded": True, "degraded_reason": "vector path down"}
    with pytest.raises(MemoryRecallUnavailable) as excinfo:
        process_search_response(
            data,
            "real",
            "where are my keys",
            3,
            _rescore,
            tenant="tenant-degraded",
        )
    assert "degrad" in str(excinfo.value).lower()
    assert not isinstance(excinfo.value, AssertionError)


def test_degraded_true_with_hits_marks_every_hit() -> None:
    """Partial results stay usable but must carry the degraded flag."""
    data = {
        "hits": [
            {"task": "buy milk", "tenant": "tenant-degraded", "score": 0.9},
            {"task": "buy eggs", "tenant": "tenant-degraded", "score": 0.8},
        ],
        "degraded": True,
        "degraded_reason": "orm fallback",
    }
    hits = process_search_response(
        data,
        "real",
        "buy",
        3,
        _rescore,
        tenant="tenant-degraded",
    )
    assert hits, "degraded=true with matches must still return the matches"
    assert all(h.degraded is True for h in hits)
    assert all(h.payload.get("task") in ("buy milk", "buy eggs") for h in hits)


def test_degraded_false_or_absent_is_ordinary_success() -> None:
    data = {"hits": [{"task": "a", "tenant": "tenant-degraded", "score": 1.0}]}
    hits = process_search_response(
        data, "real", "a", 3, _rescore, tenant="tenant-degraded"
    )
    assert len(hits) == 1
    assert hits[0].degraded is False


def test_genuine_empty_without_degraded_stays_successful_empty() -> None:
    data = {"hits": [], "degraded": False}
    assert (
        process_search_response(
            data, "real", "zzz", 3, _rescore, tenant="tenant-degraded"
        )
        == []
    )


def test_degraded_truthy_string_also_fails_closed() -> None:
    """Any truthy degraded marker is honoured, not just JSON true."""
    data = {"hits": [], "degraded": "true"}
    with pytest.raises(MemoryRecallUnavailable):
        process_search_response(
            data, "real", "q", 3, _rescore, tenant="tenant-degraded"
        )


def test_normalize_hits_preserves_raw_for_degraded_detection() -> None:
    """The raw response is reachable so callers can inspect degraded_reason."""
    item = {"task": "t", "score": 0.5, "tenant": "tenant-degraded"}
    hits = normalize_recall_hits({"hits": [item], "degraded": True})
    assert hits and hits[0].raw is not None
