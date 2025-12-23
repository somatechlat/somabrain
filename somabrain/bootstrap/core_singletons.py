"""Core Singletons - Application-level singleton instances.

Extracted from somabrain/app.py per vibe-compliance-audit spec.
Provides factory functions for creating core application singletons.

These singletons are created during application startup and shared
across all request handlers.
"""

from __future__ import annotations

import logging
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
        dim=cfg.embed_dim,
        cfg=MTWMConfig(
            per_tenant_capacity=max(cfg.wm_per_tenant_capacity, cfg.wm_size),
            max_tenants=cfg.mtwm_max_tenants,
            recency_time_scale=cfg.wm_recency_time_scale,
            recency_max_steps=cfg.wm_recency_max_steps,
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

    columns = max(1, int(cfg.micro_circuits))
    per_col_capacity = max(
        16,
        int((cfg.wm_size + columns - 1) // columns),
    )

    return MultiColumnWM(
        dim=cfg.embed_dim,
        cfg=MCConfig(
            columns=columns,
            per_col_capacity=per_col_capacity,
            vote_temperature=cfg.micro_vote_temperature,
            max_tenants=cfg.micro_max_tenants,
            recency_time_scale=cfg.wm_recency_time_scale,
            recency_max_steps=cfg.wm_recency_max_steps,
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
            max_anchors=cfg.hrr_anchors_max,
            decay_lambda=cfg.hrr_decay_lambda,
            min_confidence=cfg.hrr_cleanup_min_confidence,
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

    return QuotaManager(QuotaConfig(daily_writes=cfg.write_daily_limit))


def create_rate_limiter(cfg):
    """Create the RateLimiter singleton.

    Args:
        cfg: Application configuration object.

    Returns:
        RateLimiter: The rate limiting singleton.
    """
    from somabrain.ratelimit import RateConfig, RateLimiter

    return RateLimiter(RateConfig(rps=cfg.rate_rps, burst=cfg.rate_burst))


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
            w_novelty=cfg.salience_w_novelty,
            w_error=cfg.salience_w_error,
            threshold_store=cfg.salience_threshold_store,
            threshold_act=cfg.salience_threshold_act,
            hysteresis=cfg.salience_hysteresis,
            use_soft=cfg.use_soft_salience,
            soft_temperature=cfg.use_soft_salience,
            method=cfg.salience_method,
            w_fd=cfg.salience_fd_weight,
            fd_energy_floor=cfg.salience_fd_energy_floor,
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
    if not cfg.use_meta_brain:
        return None

    from somabrain.supervisor import Supervisor, SupervisorConfig

    return Supervisor(SupervisorConfig(gain=cfg.meta_gain, limit=cfg.meta_limit))


def create_exec_controller(cfg):
    """Create the ExecutiveController singleton if enabled.

    Args:
        cfg: Application configuration object.

    Returns:
        ExecutiveController if use_exec_controller is True, None otherwise.
    """
    if not cfg.use_exec_controller:
        return None

    from somabrain.exec_controller import ExecConfig, ExecutiveController

    return ExecutiveController(
        ExecConfig(
            window=cfg.exec_window,
            conflict_threshold=cfg.exec_conflict_threshold,
            explore_boost_k=cfg.exec_explore_boost_k,
            use_bandits=bool(getattr(cfg, "exec_use_bandits", False)),
            bandit_eps=cfg.exec_bandit_eps,
        )
    )


def create_drift_monitor(cfg):
    """Create the DriftMonitor singleton if enabled.

    Args:
        cfg: Application configuration object.

    Returns:
        DriftMonitor if use_drift_monitor is True, None otherwise.
    """
    if not cfg.use_drift_monitor:
        return None

    from somabrain.controls.drift_monitor import DriftConfig, DriftMonitor

    return DriftMonitor(
        cfg.embed_dim,
        DriftConfig(window=cfg.drift_window, threshold=cfg.drift_threshold),
    )


def create_sdr_encoder(cfg):
    """Create the SDR encoder if enabled.

    Args:
        cfg: Application configuration object.

    Returns:
        SDREncoder if use_sdr_prefilter is True, None otherwise.
    """
    if not cfg.use_sdr_prefilter:
        return None

    from somabrain.sdr import SDREncoder

    return SDREncoder(dim=cfg.sdr_dim, density=cfg.sdr_density)


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
    client = MemoryClient(cfg)
    
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
        dsn=getattr(cfg, "database_url", "postgresql://vibe:vibe@localhost/somabrain"),
        table_name="fnom_kv" # Use separate table or implicit segregation via keys
    )
    
    # Use separate collection or partition for FNOM if possible, or share
    vector_store = MilvusVectorStore(
        host=getattr(cfg, "milvus_host", "localhost"),
        port=getattr(cfg, "milvus_port", "19530"),
        collection_name="soma_fnom_memory"
    )

    return PersistentFNOM(
        kv_store=kv_store,
        vector_store=vector_store,
        namespace="fnom",
        embedder=embedder
    )

