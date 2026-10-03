"""Singleton Initialization - Core singleton factory functions.

Extracted from somabrain/app.py per global-architecture-refactor spec.
Provides factory functions for creating application-level singletons.

This module is HIGH RISK due to tight coupling with runtime.py module loading.
Changes should be tested thoroughly before deployment.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from django.conf import settings

from somabrain.embed_dim import resolve_embed_dim

if TYPE_CHECKING:
    from somabrain.admin.core.learning.prediction import BudgetedPredictor
    from somabrain.admin.core.quantum import QuantumLayer

logger = logging.getLogger("somabrain.bootstrap.singletons")


# ---------------------------------------------------------------------------
# Predictor Factory
# ---------------------------------------------------------------------------


def make_predictor(cfg) -> BudgetedPredictor:
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
    from somabrain.admin.core.learning.prediction import (
        BudgetedPredictor,
        LLMPredictor,
        MahalanobisPredictor,
        SlowPredictor,
    )

    provider_override = settings.SOMABRAIN_PREDICTOR_PROVIDER
    provider = str(
        
            provider_override
            or getattr(settings, "SOMABRAIN_PREDICTOR_PROVIDER", "mahal")
            or "mahal"
        
    ).lower()

    if provider in ("stub", "baseline"):
        # Always reject synthetic providers — this enforces the real-backend policy.
        raise RuntimeError(
            f"Predictor provider '{provider}' is not permitted. "
            "Set SOMABRAIN_PREDICTOR_PROVIDER=mahal or llm."
        )

    if provider in ("mahal", "mahalanobis"):
        base = MahalanobisPredictor(alpha=0.01)
    elif provider == "slow":
        base = SlowPredictor(
            delay_ms=getattr(settings, "SOMABRAIN_PREDICTOR_TIMEOUT_MS", 1000) * 2
        )
    elif provider == "llm":
        base = LLMPredictor(
            endpoint=getattr(settings, "SOMABRAIN_PREDICTOR_LLM_ENDPOINT", None),
            token=getattr(settings, "SOMABRAIN_PREDICTOR_LLM_TOKEN", None),
            timeout_ms=getattr(settings, "SOMABRAIN_PREDICTOR_TIMEOUT_MS", 1000),
        )
    else:
        # If an unknown provider is requested, fall back to Mahalanobis so we
        # keep behaviour deterministic and production-ready.
        logger.warning(
            "Unknown predictor provider '%s', falling back to mahalanobis",
            provider,
        )
        base = MahalanobisPredictor(alpha=0.01)

    return BudgetedPredictor(
        base, timeout_ms=getattr(settings, "SOMABRAIN_PREDICTOR_TIMEOUT_MS", 1000)
    )


# ---------------------------------------------------------------------------
# Quantum Layer Factory
# ---------------------------------------------------------------------------


def make_quantum_layer(cfg) -> QuantumLayer | None:
    """Create the optional quantum layer for HRR-based operations.

    Args:
        cfg: Application configuration object with HRR settings.

    Returns:
        QuantumLayer if cfg.use_hrr is True and initialization succeeds,
        None otherwise.
    """
    if not getattr(settings, "SOMABRAIN_USE_HRR", False):
        return None

    try:
        from somabrain.admin.core.quantum import HRRConfig, QuantumLayer

        hrr_cfg = HRRConfig(
            dim=getattr(settings, "SOMABRAIN_HRR_DIM", 1024),
            seed=getattr(settings, "SOMABRAIN_HRR_SEED", 42),
            binding_method=getattr(
                settings, "SOMABRAIN_MATH_BINDING_METHOD", "circular"
            ),
            sparsity=getattr(settings, "SOMABRAIN_MATH_BHDC_SPARSITY", 0.1),
            binary_mode=getattr(settings, "SOMABRAIN_MATH_BHDC_BINARY_MODE", False),
            mix=getattr(settings, "SOMABRAIN_MATH_BHDC_MIX", 0.5),
            binding_seed=getattr(settings, "SOMABRAIN_MATH_BINDING_SEED", 42),
            binding_model_version=getattr(
                settings, "SOMABRAIN_MATH_BINDING_MODEL_VERSION", "v1"
            ),
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

    from somabrain.admin.core.embeddings import make_embedder

    embedder = make_embedder(cfg, quantum=quantum)

    # Determine embedding dimension
    try:
        embed_dim = int(embedder.dim)
    except Exception:
        try:
            embed_dim = int(
                np.asarray(embedder.embed("___dim_probe___"), dtype=float).size
            )
        except Exception as exc:
            raise RuntimeError("embedder failed to produce vector dimension") from exc

    # Ensure config reflects the actual embedder dimension at runtime
    current_embed_dim = resolve_embed_dim(settings)
    if current_embed_dim != embed_dim:
        raise RuntimeError(
            f"SOMABRAIN_EMBED_DIM={current_embed_dim} does not match provider "
            f"dim={embed_dim}; refusing to guess a vector dim"
        )

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
    if getattr(settings, "SOMABRAIN_SALIENCE_METHOD", "dense").lower() != "fd":
        return None

    from somabrain.admin.core.learning.salience import FDSalienceSketch

    embed_dim = resolve_embed_dim(settings)
    return FDSalienceSketch(
        dim=int(embed_dim),
        rank=max(
            1,
            min(
                int(getattr(settings, "SOMABRAIN_SALIENCE_FD_RANK", 32)), int(embed_dim)
            ),
        ),
        decay=float(getattr(settings, "SOMABRAIN_SALIENCE_FD_DECAY", 0.05)),
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
    from somabrain.admin.core.learning.scoring import UnifiedScorer

    return UnifiedScorer(
        w_cosine=getattr(settings, "SOMABRAIN_SCORER_W_COSINE", 0.5),
        w_fd=getattr(settings, "SOMABRAIN_SCORER_W_FD", 0.2),
        w_recency=getattr(settings, "SOMABRAIN_SCORER_W_RECENCY", 0.3),
        weight_min=getattr(settings, "SOMABRAIN_SCORER_WEIGHT_MIN", 0.0),
        weight_max=getattr(settings, "SOMABRAIN_SCORER_WEIGHT_MAX", 1.0),
        recency_tau=getattr(settings, "SOMABRAIN_SCORER_RECENCY_TAU", 3600.0),
        fd_backend=fd_sketch,
    )


# ---------------------------------------------------------------------------
# Runtime Accessors
# ---------------------------------------------------------------------------
#
# These used to live as attributes on ``somabrain.app``. That module is gone.
# The DI container (``somabrain.core.container``) is the home for singletons
# now, and this is the same register-on-first-use pattern
# ``somabrain.journal.local_journal`` and ``somabrain.metrics.interface`` use.


def _singleton(name: str, factory):
    """Register ``factory`` under ``name`` on first use, then return the instance.

    Registration is idempotent: an already-registered name is left alone so a
    test that registered a replacement keeps it.
    """
    from somabrain.core.container import container

    if not container.has(name):
        container.register(name, factory)
    return container.get(name)


def get_predictor():
    """The process-wide predictor. Same object every call."""
    return _singleton("predictor", lambda: make_predictor(settings))


def get_amygdala():
    """The process-wide salience scorer. Same object every call."""
    from somabrain.bootstrap.core_singletons import create_amygdala

    return _singleton("amygdala", lambda: create_amygdala(settings))


def get_neuromodulators():
    """Per-tenant neuromodulator state. One store, keyed by tenant inside."""
    from somabrain.runtime.neuromodulators import PerTenantNeuromodulators

    return _singleton("per_tenant_neuromodulators", PerTenantNeuromodulators)


def get_personality_store():
    """Per-tenant personality traits. One store, keyed by tenant inside."""
    from somabrain.admin.cognitive.personality import PersonalityStore

    return _singleton("personality_store", PersonalityStore)
