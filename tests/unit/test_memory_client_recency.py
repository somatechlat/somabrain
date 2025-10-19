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


def _mk_client(
    cfg: Config, *, w_cosine: float = 0.0, w_recency: float = 1.0
) -> MemoryClient:
    scorer = UnifiedScorer(
        w_cosine=w_cosine,
        w_fd=0.0,
        w_recency=w_recency,
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
    cfg.recall_recency_sharpness = 1.0
    cfg.recall_recency_floor = 0.2
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
    age_seconds = 20.0
    steps = min(
        math.log1p(age_seconds / cfg.recall_recency_time_scale)
        * cfg.recall_recency_sharpness,
        cfg.recall_recency_max_steps,
    )
    recency_component = math.exp(-steps / cfg.scorer_recency_tau)
    boost = max(
        cfg.recall_recency_floor,
        math.exp(
            -(
                (age_seconds / cfg.recall_recency_time_scale)
                ** cfg.recall_recency_sharpness
            )
        ),
    )
    expected = recency_component * boost
    assert math.isclose(aged.score or 0.0, expected, rel_tol=1e-6, abs_tol=1e-7)


def test_rescore_accepts_iso8601_timestamps() -> None:
    cfg = Config()
    cfg.recall_recency_time_scale = 5.0
    cfg.recall_recency_max_steps = 32.0
    cfg.recall_recency_sharpness = 1.0
    cfg.recall_recency_floor = 0.05
    cfg.scorer_recency_tau = 2.0
    client = _mk_client(cfg)

    now = datetime.now(timezone.utc)
    iso_ts = (now - timedelta(seconds=5)).isoformat()
    hit = RecallHit(payload={"content": "iso", "timestamp": iso_ts}, score=0.1)

    ranked = client._rescore_and_rank_hits([hit], "iso query")
    assert ranked[0].payload["content"] == "iso"
    steps = (
        math.log1p(5.0 / cfg.recall_recency_time_scale) * cfg.recall_recency_sharpness
    )
    recency_component = math.exp(-steps / cfg.scorer_recency_tau)
    boost = math.exp(
        -((5.0 / cfg.recall_recency_time_scale) ** cfg.recall_recency_sharpness)
    )
    expected = recency_component * boost
    assert math.isclose(ranked[0].score or 0.0, expected, rel_tol=3e-5, abs_tol=5e-6)


def test_density_factor_applies_floor_when_margin_low() -> None:
    cfg = Config()
    cfg.scorer_recency_tau = 1.0
    cfg.recall_density_margin_target = 0.3
    cfg.recall_density_margin_floor = 0.4
    cfg.recall_density_margin_weight = 0.8
    client = _mk_client(cfg, w_cosine=1.0, w_recency=0.0)

    hit = RecallHit(payload={"content": "dense", "_cleanup_margin": 0.05}, score=None)
    ranked = client._rescore_and_rank_hits([hit], "dense")
    assert ranked[0].payload["content"] == "dense"
    assert math.isclose(
        ranked[0].score or 0.0, cfg.recall_density_margin_floor, rel_tol=1e-6
    )
