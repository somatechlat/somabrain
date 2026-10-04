"""Core Singletons - Application-level singleton instances.

Extracted from somabrain/app.py per vibe-compliance-audit spec.
Provides factory functions for creating core application singletons.

These singletons are created during application startup and shared
across all request handlers.
"""

from __future__ import annotations

from somabrain.embed_dim import resolve_embed_dim

import logging
from typing import TYPE_CHECKING, Any

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

if TYPE_CHECKING:
    from somabrain.admin.core.learning.scoring import UnifiedScorer
    from somabrain.admin.core.quantum import QuantumLayer

logger = logging.getLogger("somabrain.bootstrap.core_singletons")


def create_mt_wm(cfg, scorer: UnifiedScorer):
    """Create the MultiTenantWM singleton.

    Args:
        cfg: Application configuration object.
        scorer: UnifiedScorer instance for memory scoring.

    Returns:
        MultiTenantWM: The working memory singleton.
    """
    from somabrain.memory.wm.mt_wm import MTWMConfig, MultiTenantWM

    return MultiTenantWM(
        dim=resolve_embed_dim(settings),
        cfg=MTWMConfig(
            per_tenant_capacity=max(
                getattr(settings, "SOMABRAIN_WM_PER_TENANT_CAPACITY"),
                getattr(settings, "SOMABRAIN_WM_SIZE"),
            ),
            max_tenants=getattr(settings, "SOMABRAIN_MTWM_MAX_TENANTS"),
            recency_time_scale=getattr(
                settings, "SOMABRAIN_WM_RECENCY_TIME_SCALE", 3600
            ),
            recency_max_steps=getattr(settings, "SOMABRAIN_WM_RECENCY_MAX_STEPS"),
        ),
        scorer=scorer,
    )


def create_mc_wm(cfg, scorer: UnifiedScorer):
    """Create the MultiColumnWM singleton.

    Args:
        cfg: Application configuration object.
        scorer: UnifiedScorer instance for memory scoring.

    Returns:
        MultiColumnWM: The multi-column working memory singleton.
    """
    from somabrain.admin.cognitive.microcircuits import MCConfig, MultiColumnWM

    columns = max(1, int(getattr(settings, "SOMABRAIN_MICRO_CIRCUITS")))
    per_col_capacity = max(
        16,
        int((getattr(settings, "SOMABRAIN_WM_SIZE") + columns - 1) // columns),
    )

    return MultiColumnWM(
        dim=resolve_embed_dim(settings),
        cfg=MCConfig(
            columns=columns,
            per_col_capacity=per_col_capacity,
            vote_temperature=getattr(settings, "SOMABRAIN_MICRO_VOTE_TEMPERATURE"),
            max_tenants=getattr(settings, "SOMABRAIN_MICRO_MAX_TENANTS"),
            recency_time_scale=getattr(
                settings, "SOMABRAIN_WM_RECENCY_TIME_SCALE", 3600
            ),
            recency_max_steps=getattr(settings, "SOMABRAIN_WM_RECENCY_MAX_STEPS"),
        ),
        scorer=scorer,
    )


def create_mt_ctx(cfg, quantum: QuantumLayer | None):
    """Create the MultiTenantHRRContext singleton.

    Args:
        cfg: Application configuration object.
        quantum: Optional QuantumLayer for HRR operations.

    Returns:
        MultiTenantHRRContext if quantum is available, None otherwise.
    """
    if quantum is None:
        return None

    from somabrain.admin.core.context_hrr import HRRContextConfig
    from somabrain.memory.mt_context import MultiTenantHRRContext

    return MultiTenantHRRContext(
        quantum,
        HRRContextConfig(
            max_anchors=getattr(settings, "SOMABRAIN_HRR_ANCHORS_MAX"),
            decay_lambda=getattr(settings, "SOMABRAIN_HRR_DECAY_LAMBDA"),
            min_confidence=getattr(
                settings, "SOMABRAIN_HRR_CLEANUP_MIN_CONFIDENCE", 0.1
            ),
        ),
        max_tenants=1000,
    )


def create_amygdala(cfg, fd_sketch: Any = None):
    """Create the AmygdalaSalience singleton.

    Args:
        cfg: Application configuration object.
        fd_sketch: Optional FDSalienceSketch for FD-based scoring.

    Returns:
        AmygdalaSalience: The salience computation singleton.
    """
    from somabrain.admin.cognitive.amygdala import AmygdalaSalience, SalienceConfig

    return AmygdalaSalience(
        SalienceConfig(
            w_novelty=getattr(settings, "SOMABRAIN_SALIENCE_W_NOVELTY"),
            w_error=getattr(settings, "SOMABRAIN_SALIENCE_W_ERROR"),
            threshold_store=getattr(
                settings, "SOMABRAIN_SALIENCE_THRESHOLD_STORE", 0.6
            ),
            threshold_act=getattr(settings, "SOMABRAIN_SALIENCE_THRESHOLD_ACT"),
            hysteresis=getattr(settings, "SOMABRAIN_SALIENCE_HYSTERESIS"),
            use_soft=getattr(settings, "SOMABRAIN_USE_SOFT_SALIENCE"),
            soft_temperature=getattr(
                settings, "SOMABRAIN_SOFT_SALIENCE_TEMPERATURE", 1.0
            ),
            method=getattr(settings, "SOMABRAIN_SALIENCE_METHOD"),
            w_fd=getattr(settings, "SOMABRAIN_SALIENCE_FD_WEIGHT"),
            fd_energy_floor=getattr(
                settings, "SOMABRAIN_SALIENCE_FD_ENERGY_FLOOR", 0.01
            ),
        ),
        fd_backend=fd_sketch,
    )


def create_hippocampus():
    """Create the Hippocampus singleton.

    Returns:
        Hippocampus: The consolidation singleton.
    """
    from somabrain.admin.cognitive.hippocampus import ConsolidationConfig, Hippocampus

    return Hippocampus(ConsolidationConfig())


def create_supervisor(cfg):
    """Create the Supervisor singleton if enabled.

    Args:
        cfg: Application configuration object.

    Returns:
        Supervisor if use_meta_brain is True, None otherwise.
    """
    if not getattr(settings, "SOMABRAIN_USE_META_BRAIN"):
        return None

    from somabrain.runtime.supervisor import Supervisor, SupervisorConfig

    return Supervisor(
        SupervisorConfig(
            gain=getattr(settings, "SOMABRAIN_META_GAIN"),
            limit=getattr(settings, "SOMABRAIN_META_LIMIT"),
        )
    )


def create_exec_controller(cfg):
    """Create the ExecutiveController singleton if enabled.

    Args:
        cfg: Application configuration object.

    Returns:
        ExecutiveController if use_exec_controller is True, None otherwise.
    """
    if not getattr(settings, "SOMABRAIN_USE_EXEC_CONTROLLER"):
        return None

    from somabrain.planning.exec_controller import ExecConfig, ExecutiveController

    return ExecutiveController(
        ExecConfig(
            window=getattr(settings, "SOMABRAIN_EXEC_WINDOW"),
            conflict_threshold=getattr(
                settings, "SOMABRAIN_EXEC_CONFLICT_THRESHOLD", 0.4
            ),
            explore_boost_k=getattr(settings, "SOMABRAIN_EXEC_EXPLORE_BOOST_K"),
            use_bandits=bool(getattr(settings, "SOMABRAIN_EXEC_USE_BANDITS")),
            bandit_eps=getattr(settings, "SOMABRAIN_EXEC_BANDIT_EPS"),
        )
    )


def create_drift_monitor(cfg):
    """Create the DriftMonitor singleton if enabled.

    Args:
        cfg: Application configuration object.

    Returns:
        DriftMonitor if use_drift_monitor is True, None otherwise.
    """
    if not getattr(settings, "SOMABRAIN_USE_DRIFT_MONITOR"):
        return None

    from somabrain.controls.drift_monitor import DriftConfig, DriftMonitor

    return DriftMonitor(
        resolve_embed_dim(settings),
        DriftConfig(
            window=getattr(settings, "SOMABRAIN_DRIFT_WINDOW"),
            threshold=getattr(settings, "SOMABRAIN_DRIFT_THRESHOLD"),
        ),
    )


def create_sdr_encoder(cfg):
    """Create the SDR encoder if enabled.

    Args:
        cfg: Application configuration object.

    Returns:
        SDREncoder if use_sdr_prefilter is True, None otherwise.
    """
    if not getattr(settings, "SOMABRAIN_USE_SDR_PREFILTER"):
        return None

    from somabrain.admin.core.sdr import SDREncoder

    return SDREncoder(
        dim=getattr(settings, "SOMABRAIN_SDR_DIM"),
        density=getattr(settings, "SOMABRAIN_SDR_DENSITY"),
    )


def create_ewma_monitors():
    """Create EWMA monitoring instances.

    Returns:
        dict: Dictionary containing EWMA instances for various metrics.
    """
    from somabrain.core.utils.stats import EWMA

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

    from somabrain.admin.brain.unified_core import UnifiedBrainCore

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
    from somabrain.admin.brain.adapters import FractalClientAdapter

    # We need a memory client instance.
    # In strictly layered architecture, we might create a dedicated one here
    # or access the global one. For bootstrap, we instantiate a client.
    from somabrain.memory.client import MemoryClient

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
    from somafractalmemory.implementations.milvus_vector import MilvusVectorStore
    from somafractalmemory.implementations.postgres_kv import PostgresKeyValueStore

    from somabrain.admin.brain.fnom import PersistentFNOM

    # Reuse valid connection parameters for shared persistence layer
    # Segregate data via explicit namespacing
    postgres_dsn = getattr(settings, "SOMABRAIN_POSTGRES_DSN")
    if not postgres_dsn:
        raise ImproperlyConfigured(
            "SOMABRAIN_POSTGRES_DSN must be configured before creating PersistentFNOM"
        )

    kv_store = PostgresKeyValueStore(
        dsn=postgres_dsn,
        table_name="fnom_kv",
    )

    milvus_host = getattr(settings, "SOMABRAIN_MILVUS_HOST")
    if not milvus_host:
        raise RuntimeError(
            "SOMABRAIN_MILVUS_HOST is not configured — refusing to invent a vector-store host"
        )
    milvus_port = getattr(settings, "SOMABRAIN_MILVUS_PORT")
    if not milvus_port:
        raise RuntimeError(
            "SOMABRAIN_MILVUS_PORT is not configured — refusing to invent a vector-store port"
        )
    milvus_collection = getattr(settings, "SOMABRAIN_MILVUS_COLLECTION")
    if not milvus_collection:
        raise RuntimeError(
            "SOMABRAIN_MILVUS_COLLECTION is not configured — refusing to invent a collection name"
        )
    vector_store = MilvusVectorStore(
        host=milvus_host,
        port=milvus_port,
        collection_name=milvus_collection,
    )

    return PersistentFNOM(
        kv_store=kv_store,
        vector_store=vector_store,
        namespace="fnom",
        embedder=embedder,
    )
