import math
from datetime import datetime, timedelta, timezone

import numpy as np

from somabrain.config import Config
from somabrain.memory_client import MemoryClient, RecallHit
from somabrain.scoring import UnifiedScorer


class _StaticEmbedder:
    """Deterministic embedder for unit tests."""

    def embed(self, text: str) -> np.ndarray:
        length = float(len(text))
        checksum = float(sum(ord(ch) for ch in text) % 1024)
        vec = np.array([length or 1.0, checksum or 1.0], dtype=np.float32)
        norm = float(np.linalg.norm(vec))
        if norm > 0:
            vec /= norm
        return vec


def _mk_client(cfg: Config) -> MemoryClient:
    scorer = UnifiedScorer(
        w_cosine=0.0,
        w_fd=0.0,
        w_recency=1.0,
        weight_min=0.0,
        weight_max=1.0,
        recency_tau=cfg.scorer_recency_tau,
    )
    client = MemoryClient.__new__(MemoryClient)
    client.cfg = cfg
    client._scorer = scorer
    client._embedder = _StaticEmbedder()
    return client


def test_rescore_bounds_recency_by_configured_cap() -> None:
    cfg = Config()
    cfg.recall_recency_time_scale = 2.0
    cfg.recall_recency_max_steps = 4.0
    cfg.scorer_recency_tau = 1.0
    client = _mk_client(cfg)

    now = datetime.now(timezone.utc).timestamp()
    hits = [
        RecallHit(payload={"content": "fresh", "timestamp": now}, score=0.2),
        RecallHit(payload={"content": "aged", "timestamp": now - 20}, score=0.2),
    ]

    ranked = client._rescore_and_rank_hits(hits, "unit-test query")
    assert ranked[0].payload["content"] == "fresh"

    aged = next(hit for hit in ranked if hit.payload["content"] == "aged")
    expected = math.exp(-4.0 / cfg.scorer_recency_tau)
    assert math.isclose(aged.score or 0.0, expected, rel_tol=1e-6)


def test_rescore_accepts_iso8601_timestamps() -> None:
    cfg = Config()
    cfg.recall_recency_time_scale = 5.0
    cfg.recall_recency_max_steps = 32.0
    cfg.scorer_recency_tau = 2.0
    client = _mk_client(cfg)

    now = datetime.now(timezone.utc)
    iso_ts = (now - timedelta(seconds=5)).isoformat()
    hit = RecallHit(payload={"content": "iso", "timestamp": iso_ts}, score=0.1)

    ranked = client._rescore_and_rank_hits([hit], "iso query")
    assert ranked[0].payload["content"] == "iso"
    steps = min(5.0 / cfg.recall_recency_time_scale, cfg.recall_recency_max_steps)
    expected = math.exp(-steps / cfg.scorer_recency_tau)
    assert math.isclose(ranked[0].score or 0.0, expected, rel_tol=1e-5)
