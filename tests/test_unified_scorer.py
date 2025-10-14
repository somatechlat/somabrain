import numpy as np

from somabrain.salience import FDSalienceSketch
from somabrain.scoring import UnifiedScorer


def test_unified_scorer_combines_components():
    sketch = FDSalienceSketch(dim=3, rank=2, decay=1.0)
    sketch.observe(np.array([1.0, 0.0, 0.0]))
    sketch.observe(np.array([0.0, 1.0, 0.0]))

    scorer = UnifiedScorer(
        w_cosine=0.5,
        w_fd=0.3,
        w_recency=0.2,
        weight_min=0.0,
        weight_max=1.0,
        recency_tau=16.0,
        fd_backend=sketch,
    )
    query = np.array([1.0, 0.0, 0.0])
    candidate = np.array([1.0, 0.0, 0.0])
    score = scorer.score(query, candidate, recency_steps=0)
    assert 0.99 <= score <= 1.0


def test_unified_scorer_recency_decay():
    scorer = UnifiedScorer(
        w_cosine=1.0,
        w_fd=0.0,
        w_recency=0.0,
        weight_min=0.0,
        weight_max=1.0,
        recency_tau=8.0,
    )
    query = np.array([1.0, 0.0])
    candidate = np.array([1.0, 0.0])
    fresh = scorer.score(query, candidate, recency_steps=0)
    stale = scorer.score(query, candidate, recency_steps=80)
    assert fresh == 1.0
    assert stale == 1.0  # cosine only

    scorer_boost = UnifiedScorer(
        w_cosine=0.0,
        w_fd=0.0,
        w_recency=1.0,
        weight_min=0.0,
        weight_max=1.0,
        recency_tau=8.0,
    )
    recency_fresh = scorer_boost.score(query, candidate, recency_steps=0)
    recency_stale = scorer_boost.score(query, candidate, recency_steps=80)
    assert recency_fresh > recency_stale
    assert 0.0 <= recency_stale <= recency_fresh <= 1.0


def test_unified_scorer_weight_clamping():
    scorer = UnifiedScorer(
        w_cosine=2.0,
        w_fd=-1.0,
        w_recency=0.5,
        weight_min=0.0,
        weight_max=1.0,
        recency_tau=16.0,
    )
    assert scorer._weights.w_cosine == 1.0
    assert scorer._weights.w_fd == 0.0
    assert scorer._weights.w_recency == 0.5
