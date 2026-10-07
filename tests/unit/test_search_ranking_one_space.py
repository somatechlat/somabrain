"""Recall ranking must stay in ONE embedding space and never fake a zero.

Proves the BREAK 2 contract:

- a hit with no text/content/task/fact/headline/what key does NOT report
  score 0.0 — it passes the store score through (or fails closed);
- the scoring path never calls a fourth embedder (TinyDeterministicEmbedder /
  blake2b trigrams) against store vectors;
- a precomputed query vector is the only query vector used.

Production imports only. Marked ``no_django`` so the suite runs without the
memory-HTTP credential gate.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime

import numpy as np
import pytest

pytestmark = pytest.mark.no_django

from somabrain.memory.client.ranking import _rescore_and_rank_hits
from somabrain.memory.client.types import RecallHit


class _Cfg:
    SOMABRAIN_WM_RECENCY_TIME_SCALE = 60.0
    SOMABRAIN_WM_RECENCY_MAX_STEPS = 1000.0
    SOMABRAIN_RECENCY_SHARPNESS = 1.2
    SOMABRAIN_RECENCY_FLOOR = 0.05
    recall_density_margin_target = 0.2
    recall_density_margin_floor = 0.6
    recall_density_margin_weight = 0.35


class _ExplodingEmbedder:
    """Any call to embed is a foreign vector space entering the path."""

    def embed(self, text: str):
        raise AssertionError(
            "scoring path must never call embedder.embed — that is a fourth "
            "vector space (INVARIANTS §2.1)"
        )


class _CosineEchoScorer:
    """Uses the cosine term when given; never looks at the vectors."""

    def __init__(self) -> None:
        self.seen_ages: list[float | None] = []
        self.calls = 0

    def score(self, query, candidate, *, age_seconds=None, cosine=None) -> float:
        self.calls += 1
        self.seen_ages.append(age_seconds)
        if cosine is not None:
            return float(cosine)
        q = np.asarray(query, dtype=float).reshape(-1)
        c = np.asarray(candidate, dtype=float).reshape(-1)
        if q.size == 0 or c.size == 0 or q.size != c.size:
            raise AssertionError("cosine=None requires two real same-size vectors")
        denom = float(np.linalg.norm(q) * np.linalg.norm(c)) or 1.0
        return float(np.dot(q, c) / denom)


class TestNoTextKeyIsNotZero:
    """Gate 3: a correct hit with no text key must not become score 0.0."""

    def test_store_score_passes_through_without_text_key(self):
        now = datetime.now(UTC).timestamp()
        hit = RecallHit(payload={"marker": "no-text-key-here", "timestamp": now}, score=0.85)
        scorer = _CosineEchoScorer()
        ranked = _rescore_and_rank_hits(
            _Cfg(),
            scorer,
            _ExplodingEmbedder(),
            [hit],
            "anything",
            query_vec=[1.0, 0.0, 0.0],
        )
        assert ranked[0].score == pytest.approx(0.85, abs=1e-9)
        assert ranked[0].score != 0.0

    def test_store_score_without_text_key_still_applies_recency_once(self):
        age = 3600.0
        now = datetime.now(UTC).timestamp()
        hit = RecallHit(payload={"marker": "no-text", "timestamp": now - age}, score=1.0)
        scorer = _CosineEchoScorer()
        ranked = _rescore_and_rank_hits(
            _Cfg(), scorer, _ExplodingEmbedder(), [hit], "q", query_vec=[1.0, 0.0, 0.0]
        )
        # Recency is applied exactly once inside scorer.score(age_seconds=...).
        assert scorer.seen_ages == [pytest.approx(age)]
        assert ranked[0].score == pytest.approx(1.0, abs=1e-9)

    def test_no_text_no_score_with_query_vec_fails_closed(self):
        hit = RecallHit(payload={"marker": "nothing"}, score=None)
        with pytest.raises(RuntimeError, match="Refusing to invent 0.0"):
            _rescore_and_rank_hits(
                _Cfg(),
                _CosineEchoScorer(),
                _ExplodingEmbedder(),
                [hit],
                "q",
                query_vec=[1.0, 0.0, 0.0],
            )

    def test_no_text_no_score_text_only_leaves_unscored(self):
        hit = RecallHit(payload={"marker": "nothing"}, score=None)
        ranked = _rescore_and_rank_hits(
            _Cfg(), _CosineEchoScorer(), _ExplodingEmbedder(), [hit], "q"
        )
        assert ranked[0].score is None, "never a fake 0.0"


class TestNoForeignEmbedder:
    def test_precomputed_query_never_embeds(self):
        hit = RecallHit(payload={"embedding": [1.0, 0.0, 0.0]}, score=0.9)
        ranked = _rescore_and_rank_hits(
            _Cfg(),
            _CosineEchoScorer(),
            _ExplodingEmbedder(),
            [hit],
            "q",
            query_vec=[1.0, 0.0, 0.0],
        )
        assert ranked[0].score is not None

    def test_text_only_path_never_embeds_either(self):
        hit = RecallHit(payload={"marker": "x"}, score=0.7)
        ranked = _rescore_and_rank_hits(
            _Cfg(), _CosineEchoScorer(), _ExplodingEmbedder(), [hit], "q"
        )
        assert ranked[0].score == pytest.approx(0.7, abs=1e-9)

    def test_query_vec_and_stored_vec_score_in_same_space(self):
        hit = RecallHit(
            payload={"embedding": [1.0, 0.0, 0.0]},
            score=0.1,  # store hint must not override the real cosine
        )
        ranked = _rescore_and_rank_hits(
            _Cfg(),
            _CosineEchoScorer(),
            _ExplodingEmbedder(),
            [hit],
            "q",
            query_vec=[1.0, 0.0, 0.0],
        )
        assert ranked[0].score == pytest.approx(1.0, abs=1e-9)

    def test_dim_mismatch_refuses(self):
        hit = RecallHit(payload={"embedding": [1.0, 0.0]}, score=0.5)
        with pytest.raises(RuntimeError, match="embedding spaces"):
            _rescore_and_rank_hits(
                _Cfg(),
                _CosineEchoScorer(),
                _ExplodingEmbedder(),
                [hit],
                "q",
                query_vec=[1.0, 0.0, 0.0],
            )

    def test_scores_stay_finite_unit_interval(self):
        now = datetime.now(UTC).timestamp()
        hits = [
            RecallHit(payload={"embedding": [1.0, 0.0, 0.0], "timestamp": now}, score=0.5),
            RecallHit(payload={"marker": "n", "timestamp": now}, score=1.7),
        ]
        ranked = _rescore_and_rank_hits(
            _Cfg(),
            _CosineEchoScorer(),
            _ExplodingEmbedder(),
            hits,
            "q",
            query_vec=[1.0, 0.0, 0.0],
        )
        for hit in ranked:
            assert hit.score is not None
            assert math.isfinite(hit.score)
            assert 0.0 <= hit.score <= 1.0
