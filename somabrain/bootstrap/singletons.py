"""Singleton Initialization - Core singleton factory functions.

Extracted from somabrain/app.py per global-architecture-refactor spec.
Provides factory functions for creating application-level singletons.

This module is HIGH RISK due to tight coupling with runtime.py module loading.
Changes should be tested thoroughly before deployment.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

from common.config.settings import settings

if TYPE_CHECKING:
    from somabrain.prediction import BudgetedPredictor
    from somabrain.quantum import QuantumLayer

logger = logging.getLogger("somabrain.bootstrap.singletons")


# ---------------------------------------------------------------------------
# Predictor Factory
# ---------------------------------------------------------------------------


def make_predictor(cfg) -> "BudgetedPredictor":
    """Create the configured predictor.

    Disabled toy providers are no longer permitted. The default provider is
    'mahal' (Mahalanobis).

    Args:
        cfg: Application configuration object with predictor settings.

    Returns:
        BudgetedPredictor: Configured predictor instance.

    Raises:
        RuntimeError: If a disabled provider is requested.
    """
    from somabrain.prediction import (
        BudgetedPredictor,
        LLMPredictor,
        MahalanobisPredictor,
        SlowPredictor,
    )

    provider_override = settings.predictor_provider
    provider = str(
        (provider_override or getattr(cfg, "predictor_provider", "mahal") or "mahal")
    ).lower()

    if provider in ("stub", "baseline"):
        # Always disallow toy providers — this enforces the real-backend policy.
        raise RuntimeError(
            "Predictor provider 'stub' is not permitted. "
            "Set SOMABRAIN_PREDICTOR_PROVIDER=mahal or llm."
        )

    if provider in ("mahal", "mahalanobis"):
        base = MahalanobisPredictor(alpha=0.01)
    elif provider == "slow":
        base = SlowPredictor(delay_ms=cfg.predictor_timeout_ms * 2)
    elif provider == "llm":
        base = LLMPredictor(
            endpoint=getattr(cfg, "predictor_llm_endpoint", None),
            token=getattr(cfg, "predictor_llm_token", None),
            timeout_ms=cfg.predictor_timeout_ms,
        )
    else:
        # If an unknown provider is requested, fall back to Mahalanobis so we
        # keep behaviour deterministic and production-ready.
        logger.warning(
            "Unknown predictor provider '%s', falling back to mahalanobis",
            provider,
        )
        base = MahalanobisPredictor(alpha=0.01)

    return BudgetedPredictor(base, timeout_ms=cfg.predictor_timeout_ms)


# ---------------------------------------------------------------------------
# Quantum Layer Factory
# ---------------------------------------------------------------------------


def make_quantum_layer(cfg) -> Optional["QuantumLayer"]:
    """Create the optional quantum layer for HRR-based operations.

    Args:
        cfg: Application configuration object with HRR settings.

    Returns:
        QuantumLayer if cfg.use_hrr is True and initialization succeeds,
        None otherwise.
    """
    if not getattr(cfg, "use_hrr", False):
        return None

    try:
        from somabrain.quantum import HRRConfig, QuantumLayer

        hrr_cfg = HRRConfig(
            dim=cfg.hrr_dim,
            seed=cfg.hrr_seed,
            binding_method=cfg.math_binding_method,
            sparsity=cfg.math_bhdc_sparsity,
            binary_mode=cfg.math_bhdc_binary_mode,
            mix=cfg.math_bhdc_mix,
            binding_seed=cfg.math_binding_seed,
            binding_model_version=cfg.math_binding_model_version,
        )
        return QuantumLayer(hrr_cfg)
    except Exception:
        logger.exception("Failed to initialize quantum layer; HRR disabled.")
        return None


# ---------------------------------------------------------------------------
# Embedder Factory
# ---------------------------------------------------------------------------


def make_embedder_with_dim(cfg, quantum=None):
    """Create the embedder and determine its dimension.

    Args:
        cfg: Application configuration object with embedder settings.
        quantum: Optional QuantumLayer for HRR-based embeddings.

    Returns:
        tuple: (embedder, embed_dim) where embedder is the configured embedder
               and embed_dim is the vector dimension.

    Raises:
        RuntimeError: If embedder fails to produce a vector dimension.
    """
    import numpy as np
    from somabrain.embeddings import make_embedder

    embedder = make_embedder(cfg, quantum=quantum)

    # Determine embedding dimension
    try:
        embed_dim = int(getattr(embedder, "dim"))
    except Exception:
        try:
            embed_dim = int(np.asarray(embedder.embed("___dim_probe___"), dtype=float).size)
        except Exception as exc:
            raise RuntimeError("embedder failed to produce vector dimension") from exc

    # Ensure config reflects the actual embedder dimension at runtime
    if cfg.embed_dim != embed_dim:
        logger.warning(
            "config embed_dim=%s mismatch with provider dim=%s; overriding",
            cfg.embed_dim,
            embed_dim,
        )
        cfg.embed_dim = embed_dim

    return embedder, embed_dim


# ---------------------------------------------------------------------------
# FD Sketch Factory
# ---------------------------------------------------------------------------


def make_fd_sketch(cfg):
    """Create the FD salience sketch if configured.

    Args:
        cfg: Application configuration object with salience settings.

    Returns:
        FDSalienceSketch if salience_method is 'fd', None otherwise.
    """
    if getattr(cfg, "salience_method", "dense").lower() != "fd":
        return None

    from somabrain.salience import FDSalienceSketch

    return FDSalienceSketch(
        dim=int(cfg.embed_dim),
        rank=max(1, min(int(cfg.salience_fd_rank), int(cfg.embed_dim))),
        decay=float(cfg.salience_fd_decay),
    )


# ---------------------------------------------------------------------------
# Unified Scorer Factory
# ---------------------------------------------------------------------------


def make_unified_scorer(cfg, fd_sketch=None):
    """Create the unified scorer.

    Args:
        cfg: Application configuration object with scorer settings.
        fd_sketch: Optional FDSalienceSketch for FD-based scoring.

    Returns:
        UnifiedScorer: Configured scorer instance.
    """
    from somabrain.scoring import UnifiedScorer

    return UnifiedScorer(
        w_cosine=cfg.scorer_w_cosine,
        w_fd=cfg.scorer_w_fd,
        w_recency=cfg.scorer_w_recency,
        weight_min=cfg.scorer_weight_min,
        weight_max=cfg.scorer_weight_max,
        recency_tau=cfg.scorer_recency_tau,
        fd_backend=fd_sketch,
    )
