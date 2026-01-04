"""Core Singletons - Application-level singleton instances.

Extracted from somabrain/app.py per vibe-compliance-audit spec.
Provides factory functions for creating core application singletons.

These singletons are created during application startup and shared
across all request handlers.
"""

from __future__ import annotations

import logging
from django.conf import settings
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from somabrain.quantum import QuantumLayer
    from somabrain.scoring import UnifiedScorer

logger = logging.getLogger("somabrain.bootstrap.core_singletons")


def create_mt_wm(cfg, scorer: "UnifiedScorer"):
    """Create the MultiTenantWM singleton.

    Args:
        cfg: Application configuration object.
        scorer: UnifiedScorer instance for memory scoring.

    Returns:
        MultiTenantWM: The working memory singleton.
    """
    from somabrain.mt_wm import MTWMConfig, MultiTenantWM

    return MultiTenantWM(
        dim=getattr(settings, "EMBED_DIM", 256),
        cfg=MTWMConfig(
            per_tenant_capacity=max(
                getattr(settings, "SOMABRAIN_WM_PER_TENANT_CAPACITY", 1024),
                getattr(settings, "SOMABRAIN_WM_SIZE", 512)
            ),
            max_tenants=getattr(settings, "SOMABRAIN_MTWM_MAX_TENANTS", 100),
            recency_time_scale=getattr(settings, "SOMABRAIN_WM_RECENCY_TIME_SCALE", 3600),
            recency_max_steps=getattr(settings, "SOMABRAIN_WM_RECENCY_MAX_STEPS", 100),
        ),
        scorer=scorer,
    )


def create_mc_wm(cfg, scorer: "UnifiedScorer"):
    """Create the MultiColumnWM singleton.

    Args:
        cfg: Application configuration object.
        scorer: UnifiedScorer instance for memory scoring.

    Returns:
        MultiColumnWM: The multi-column working memory singleton.
    """
    from somabrain.microcircuits import MCConfig, MultiColumnWM

    columns = max(1, int(getattr(settings, "SOMABRAIN_MICRO_CIRCUITS", 4)))
    per_col_capacity = max(
        16,
        int((getattr(settings, "SOMABRAIN_WM_SIZE", 512) + columns - 1) // columns),
    )

    return MultiColumnWM(
        dim=getattr(settings, "EMBED_DIM", 256),
        cfg=MCConfig(
            columns=columns,
            per_col_capacity=per_col_capacity,
            vote_temperature=getattr(settings, "SOMABRAIN_MICRO_VOTE_TEMPERATURE", 0.5),
            max_tenants=getattr(settings, "SOMABRAIN_MICRO_MAX_TENANTS", 100),
            recency_time_scale=getattr(settings, "SOMABRAIN_WM_RECENCY_TIME_SCALE", 3600),
            recency_max_steps=getattr(settings, "SOMABRAIN_WM_RECENCY_MAX_STEPS", 100),
        ),
        scorer=scorer,
    )


def create_mt_ctx(cfg, quantum: Optional["QuantumLayer"]):
    """Create the MultiTenantHRRContext singleton.

    Args:
        cfg: Application configuration object.
        quantum: Optional QuantumLayer for HRR operations.

    Returns:
        MultiTenantHRRContext if quantum is available, None otherwise.
    """
    if quantum is None:
        return None

    from somabrain.context_hrr import HRRContextConfig
    from somabrain.mt_context import MultiTenantHRRContext

    return MultiTenantHRRContext(
        quantum,
        HRRContextConfig(
            max_anchors=getattr(settings, "SOMABRAIN_HRR_ANCHORS_MAX", 256),
            decay_lambda=getattr(settings, "SOMABRAIN_HRR_DECAY_LAMBDA", 0.05),
            min_confidence=getattr(settings, "SOMABRAIN_HRR_CLEANUP_MIN_CONFIDENCE", 0.1),
        ),
        max_tenants=1000,
    )


def create_quotas(cfg):
    """Create the QuotaManager singleton.

    Args:
        cfg: Application configuration object.

    Returns:
        QuotaManager: The quota management singleton.
    """
    from somabrain.quotas import QuotaConfig, QuotaManager

    return QuotaManager(
        QuotaConfig(daily_writes=getattr(settings, "SOMABRAIN_WRITE_DAILY_LIMIT", 10000))
    )


def create_rate_limiter(cfg):
    """Create the RateLimiter singleton.

    Args:
        cfg: Application configuration object.

    Returns:
        RateLimiter: The rate limiting singleton.
    """
    from somabrain.ratelimit import RateConfig, RateLimiter

    return RateLimiter(
        RateConfig(
            rps=getattr(settings, "SOMABRAIN_RATE_RPS", 100),
            burst=getattr(settings, "SOMABRAIN_RATE_BURST", 20)
        )
    )


def create_amygdala(cfg, fd_sketch: Any = None):
    """Create the AmygdalaSalience singleton.

    Args:
        cfg: Application configuration object.
        fd_sketch: Optional FDSalienceSketch for FD-based scoring.

    Returns:
        AmygdalaSalience: The salience computation singleton.
    """
    from somabrain.amygdala import AmygdalaSalience, SalienceConfig

    return AmygdalaSalience(
        SalienceConfig(
            w_novelty=getattr(settings, "SOMABRAIN_SALIENCE_W_NOVELTY", 0.5),
            w_error=getattr(settings, "SOMABRAIN_SALIENCE_W_ERROR", 0.3),
            threshold_store=getattr(settings, "SOMABRAIN_SALIENCE_THRESHOLD_STORE", 0.6),
            threshold_act=getattr(settings, "SOMABRAIN_SALIENCE_THRESHOLD_ACT", 0.4),
            hysteresis=getattr(settings, "SOMABRAIN_SALIENCE_HYSTERESIS", 0.05),
            use_soft=getattr(settings, "SOMABRAIN_USE_SOFT_SALIENCE", True),
            soft_temperature=getattr(settings, "SOMABRAIN_SOFT_SALIENCE_TEMPERATURE", 1.0),
            method=getattr(settings, "SOMABRAIN_SALIENCE_METHOD", "hybrid"),
            w_fd=getattr(settings, "SOMABRAIN_SALIENCE_FD_WEIGHT", 0.1),
            fd_energy_floor=getattr(settings, "SOMABRAIN_SALIENCE_FD_ENERGY_FLOOR", 0.01),
        ),
        fd_backend=fd_sketch,
    )


def create_hippocampus():
    """Create the Hippocampus singleton.

    Returns:
        Hippocampus: The consolidation singleton.
    """
    from somabrain.hippocampus import ConsolidationConfig, Hippocampus

    return Hippocampus(ConsolidationConfig())


def create_supervisor(cfg):
    """Create the Supervisor singleton if enabled.

    Args:
        cfg: Application configuration object.

    Returns:
        Supervisor if use_meta_brain is True, None otherwise.
    """
    if not getattr(settings, "SOMABRAIN_USE_META_BRAIN", False):
        return None

    from somabrain.supervisor import Supervisor, SupervisorConfig

    return Supervisor(
        SupervisorConfig(
            gain=getattr(settings, "SOMABRAIN_META_GAIN", 0.1),
            limit=getattr(settings, "SOMABRAIN_META_LIMIT", 1.0)
        )
    )


def create_exec_controller(cfg):
    """Create the ExecutiveController singleton if enabled.

    Args:
        cfg: Application configuration object.

    Returns:
        ExecutiveController if use_exec_controller is True, None otherwise.
    """
    if not getattr(settings, "SOMABRAIN_USE_EXEC_CONTROLLER", False):
        return None

    from somabrain.exec_controller import ExecConfig, ExecutiveController

    return ExecutiveController(
        ExecConfig(
            window=getattr(settings, "SOMABRAIN_EXEC_WINDOW", 64),
            conflict_threshold=getattr(settings, "SOMABRAIN_EXEC_CONFLICT_THRESHOLD", 0.4),
            explore_boost_k=getattr(settings, "SOMABRAIN_EXEC_EXPLORE_BOOST_K", 1.2),
            use_bandits=bool(getattr(settings, "SOMABRAIN_EXEC_USE_BANDITS", False)),
            bandit_eps=getattr(settings, "SOMABRAIN_EXEC_BANDIT_EPS", 0.1),
        )
    )


def create_drift_monitor(cfg):
    """Create the DriftMonitor singleton if enabled.

    Args:
        cfg: Application configuration object.

    Returns:
        DriftMonitor if use_drift_monitor is True, None otherwise.
    """
    if not getattr(settings, "SOMABRAIN_USE_DRIFT_MONITOR", False):
        return None

    from somabrain.controls.drift_monitor import DriftConfig, DriftMonitor

    return DriftMonitor(
        getattr(settings, "EMBED_DIM", 256),
        DriftConfig(
            window=getattr(settings, "SOMABRAIN_DRIFT_WINDOW", 256),
            threshold=getattr(settings, "SOMABRAIN_DRIFT_THRESHOLD", 0.3)
        ),
    )


def create_sdr_encoder(cfg):
    """Create the SDR encoder if enabled.

    Args:
        cfg: Application configuration object.

    Returns:
        SDREncoder if use_sdr_prefilter is True, None otherwise.
    """
    if not getattr(settings, "SOMABRAIN_USE_SDR_PREFILTER", False):
        return None

    from somabrain.sdr import SDREncoder

    return SDREncoder(
        dim=getattr(settings, "SOMABRAIN_SDR_DIM", 2048),
        density=getattr(settings, "SOMABRAIN_SDR_DENSITY", 0.02)
    )


def create_ewma_monitors():
    """Create EWMA monitoring instances.

    Returns:
        dict: Dictionary containing EWMA instances for various metrics.
    """
    from somabrain.stats import EWMA

    return {
        "novelty": EWMA(alpha=0.05),
        "error": EWMA(alpha=0.05),
        "store_rate": EWMA(alpha=0.02),
        "act_rate": EWMA(alpha=0.02),
    }


def create_unified_brain(fnom_memory: Any, fractal_memory: Any, neuromods: Any):
    """Create the UnifiedBrainCore singleton if memories are available.

    Args:
        fnom_memory: FNOM memory instance.
        fractal_memory: Fractal memory instance.
        neuromods: Neuromodulators instance.

    Returns:
        UnifiedBrainCore if both memories are available, None otherwise.
    """
    if fnom_memory is None or fractal_memory is None:
        return None

    from somabrain.brain import UnifiedBrainCore

    return UnifiedBrainCore(fractal_memory, fnom_memory, neuromods)


# ---------------------------------------------------------------------------
# Fractal Memory & FNOM Factories (Persistent)
# ---------------------------------------------------------------------------


def create_fractal_memory(cfg):
    """Create the Fractal Memory interface (VIBE: Single Point of Access).

    Instead of creating a second direct DB connection (which violates the
    'Single Point of Access' rule and duplicates logic), this factory
    returns an adapter that routes all operations through the centralized
    MemoryClient (via HTTP to the specific Memory Service).

    Args:
        cfg: Application configuration.

    Returns:
        FractalClientAdapter: VIBE-compliant interface to the memory system.
    """
    from somabrain.brain.adapters import FractalClientAdapter
    # We need a memory client instance. 
    # In strictly layered architecture, we might create a dedicated one here
    # or access the global one. For bootstrap, we instantiate a client.
    from somabrain.memory_client import MemoryClient
    
    # Instantiate client configured for the specific namespace if needed, 
    # or standard config.
    client = MemoryClient(settings)
    
    return FractalClientAdapter(client)



def create_fnom_memory(cfg, embedder):
    """Create the PersistentFNOM instance.

    Args:
        cfg: Application configuration object.
        embedder: Embedding model instance for retrieval.

    Returns:
        PersistentFNOM: The persistent FNOM instance.
    """
    from somabrain.brain.fnom import PersistentFNOM
    from somafractalmemory.implementations.postgres_kv import PostgresKeyValueStore
    from somafractalmemory.implementations.milvus_vector import MilvusVectorStore
    
    # Reuse valid connection parameters for shared persistence layer
    # Segregate data via explicit namespacing
    kv_store = PostgresKeyValueStore(
        dsn=getattr(
            settings,
            "SOMABRAIN_POSTGRES_DSN",
            "postgresql://vibe:vibe@localhost/somabrain"
        ),
        table_name="fnom_kv"
    )

    vector_store = MilvusVectorStore(
        host=getattr(settings, "MILVUS_HOST", "localhost"),
        port=getattr(settings, "MILVUS_PORT", "19530"),
        collection_name="soma_fnom_memory"
    )

    return PersistentFNOM(
        kv_store=kv_store,
        vector_store=vector_store,
        namespace="fnom",
        embedder=embedder
    )
