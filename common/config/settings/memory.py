"""Memory settings for SomaBrain.

This module contains configuration for the memory subsystem:
- Memory HTTP service
- Memory weighting and degradation
- Working memory configuration
- Tiered memory cleanup
- Scorer weights
"""

from __future__ import annotations

from typing import Optional

from common.config.settings.base import (
    BaseSettings,
    Field,
    _bool_env,
    _float_env,
    _int_env,
    _str_env,
    _yaml_get,
)


class MemorySettingsMixin(BaseSettings):
    """Memory-related settings mixin."""

    # Memory HTTP service
    memory_http_host: Optional[str] = Field(
        default=_str_env("SOMABRAIN_MEMORY_HTTP_HOST") or _str_env("MEMORY_HTTP_HOST")
    )
    memory_http_port: Optional[int] = Field(
        default=_int_env("SOMABRAIN_MEMORY_HTTP_PORT", _int_env("MEMORY_HTTP_PORT", 0))
    )
    memory_http_scheme: Optional[str] = Field(
        default=_str_env("SOMABRAIN_MEMORY_HTTP_SCHEME")
        or _str_env("MEMORY_HTTP_SCHEME")
        or "http"
    )
    memory_http_endpoint: str = Field(
        default_factory=lambda: _str_env("SOMABRAIN_MEMORY_HTTP_ENDPOINT")
        or _str_env("MEMORY_SERVICE_URL")
        or "http://localhost:9595"
    )
    memory_http_token: Optional[str] = Field(
        default=_str_env("SOMABRAIN_MEMORY_HTTP_TOKEN")
    )
    memory_max: str = Field(
        default_factory=lambda: _str_env("SOMABRAIN_MEMORY_MAX", "10GB")
    )
    memory_db_path: str = Field(default=_str_env("MEMORY_DB_PATH", "./data/memory.db"))

    # Memory weighting
    memory_enable_weighting: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_FF_MEMORY_WEIGHTING", False)
        or _bool_env("SOMABRAIN_MEMORY_ENABLE_WEIGHTING", False)
    )
    memory_phase_priors: str = Field(
        default=_str_env("SOMABRAIN_MEMORY_PHASE_PRIORS", "")
    )
    memory_quality_exp: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_MEMORY_QUALITY_EXP", 1.0)
    )
    memory_fast_ack: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_MEMORY_FAST_ACK", False)
    )

    # Memory degradation
    memory_degrade_queue: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_MEMORY_DEGRADE_QUEUE", True)
    )
    memory_degrade_readonly: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_MEMORY_DEGRADE_READONLY", False)
    )
    memory_degrade_topic: str = Field(
        default=_str_env("SOMABRAIN_MEMORY_DEGRADE_TOPIC", "memory.degraded")
    )
    memory_health_poll_interval: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_MEMORY_HEALTH_POLL_INTERVAL", 5.0)
    )
    debug_memory_client: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_DEBUG_MEMORY_CLIENT", False)
    )

    # Working memory configuration
    embed_dim: int = Field(default=256)
    wm_size: int = Field(default_factory=lambda: _int_env("SOMABRAIN_WM_SIZE", 64))
    wm_recency_time_scale: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_WM_RECENCY_TIME_SCALE", 1.0)
    )
    wm_recency_max_steps: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_WM_RECENCY_MAX_STEPS", 1000)
    )
    wm_alpha: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_WM_ALPHA", 0.6)
    )
    wm_beta: float = Field(default_factory=lambda: _float_env("SOMABRAIN_WM_BETA", 0.3))
    wm_gamma: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_WM_GAMMA", 0.1)
    )
    wm_salience_threshold: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_WM_SALIENCE_THRESHOLD", 0.4)
    )
    wm_per_col_min_capacity: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_WM_PER_COL_MIN_CAPACITY", 16)
    )
    wm_vote_softmax_floor: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_WM_VOTE_SOFTMAX_FLOOR", 1e-4)
    )
    wm_vote_entropy_eps: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_WM_VOTE_ENTROPY_EPS", 1e-9)
    )
    wm_per_tenant_capacity: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_WM_PER_TENANT_CAPACITY", 128)
    )
    mtwm_max_tenants: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_MTWM_MAX_TENANTS", 1000)
    )

    # Micro-circuit configuration
    micro_circuits: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_MICRO_CIRCUITS", 1)
    )
    micro_vote_temperature: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_MICRO_VOTE_TEMPERATURE", 0.25)
    )
    use_microcircuits: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_USE_MICROCIRCUITS", False)
    )
    micro_max_tenants: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_MICRO_MAX_TENANTS", 1000)
    )

    # Tiered memory cleanup
    tiered_memory_cleanup_backend: str = Field(
        default_factory=lambda: _str_env("SOMABRAIN_CLEANUP_BACKEND", "milvus")
        or "milvus"
    )
    tiered_memory_cleanup_topk: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_CLEANUP_TOPK", 64)
    )
    tiered_memory_cleanup_hnsw_m: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_CLEANUP_HNSW_M", 32)
    )
    tiered_memory_cleanup_hnsw_ef_construction: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_CLEANUP_HNSW_EF_CONSTRUCTION", 200)
    )
    tiered_memory_cleanup_hnsw_ef_search: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_CLEANUP_HNSW_EF_SEARCH", 128)
    )

    # Scorer weights
    scorer_w_cosine: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_SCORER_W_COSINE", 0.6)
    )
    scorer_w_fd: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_SCORER_W_FD", 0.25)
    )
    scorer_w_recency: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_SCORER_W_RECENCY", 0.15)
    )
    scorer_weight_min: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_SCORER_WEIGHT_MIN", 0.0)
    )
    scorer_weight_max: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_SCORER_WEIGHT_MAX", 1.0)
    )
    scorer_recency_tau: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_SCORER_RECENCY_TAU", 32.0)
    )

    # Retrieval weights
    retrieval_alpha: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_RETRIEVAL_ALPHA", 1.0)
    )
    retrieval_beta: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_RETRIEVAL_BETA", 0.2)
    )
    retrieval_gamma: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_RETRIEVAL_GAMMA", 0.1)
    )
    retrieval_tau: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_RETRIEVAL_TAU", 0.7)
    )
    retrieval_recency_half_life: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_RECENCY_HALF_LIFE", 60.0)
    )
    retrieval_recency_sharpness: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_RECENCY_SHARPNESS", 1.2)
    )
    retrieval_recency_floor: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_RECENCY_FLOOR", 0.05)
    )
    retrieval_density_target: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_DENSITY_TARGET", 0.2)
    )
    retrieval_density_floor: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_DENSITY_FLOOR", 0.6)
    )
    retrieval_density_weight: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_DENSITY_WEIGHT", 0.35)
    )
    retrieval_tau_min: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_TAU_MIN", 0.4)
    )
    retrieval_tau_max: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_TAU_MAX", 1.2)
    )
    retrieval_tau_increment_up: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_TAU_INC_UP", 0.1)
    )
    retrieval_tau_increment_down: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_TAU_INC_DOWN", 0.05)
    )
    retrieval_dup_ratio_threshold: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_DUP_RATIO_THRESHOLD", 0.5)
    )

    # Recall behavior
    recall_full_power: bool = Field(
        default=_bool_env("SOMABRAIN_RECALL_FULL_POWER", True)
    )
    recall_simple_defaults: bool = Field(
        default=_bool_env("SOMABRAIN_RECALL_SIMPLE_DEFAULTS", False)
    )
    recall_default_rerank: str = Field(
        default=_str_env("SOMABRAIN_RECALL_DEFAULT_RERANK", "auto")
    )
    recall_default_persist: bool = Field(
        default=_bool_env("SOMABRAIN_RECALL_DEFAULT_PERSIST", True)
    )
    recall_default_retrievers: str = Field(
        default=_str_env(
            "SOMABRAIN_RECALL_DEFAULT_RETRIEVERS", "vector,wm,graph,lexical"
        )
    )

    # Salience configuration
    salience_method: str = Field(
        default_factory=lambda: (
            _str_env("SOMABRAIN_SALIENCE_METHOD", "dense") or "dense"
        )
        .strip()
        .lower()
    )
    salience_fd_rank: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_SALIENCE_FD_RANK", 128)
    )
    salience_fd_decay: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_SALIENCE_FD_DECAY", 0.9)
    )
    salience_w_novelty: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_SALIENCE_W_NOVELTY", 0.6)
    )
    salience_w_error: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_SALIENCE_W_ERROR", 0.4)
    )
    salience_threshold_store: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_SALIENCE_THRESHOLD_STORE", 0.5)
    )
    salience_threshold_act: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_SALIENCE_THRESHOLD_ACT", 0.7)
    )
    salience_hysteresis: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_SALIENCE_HYSTERESIS", 0.1)
    )
    salience_fd_weight: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_SALIENCE_FD_WEIGHT", 0.25)
    )
    salience_fd_energy_floor: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_SALIENCE_FD_ENERGY_FLOOR", 0.9)
    )
    use_soft_salience: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_USE_SOFT_SALIENCE", False)
    )

    # Feature toggles
    use_hrr: bool = Field(default_factory=lambda: _bool_env("SOMABRAIN_USE_HRR", False))
    use_meta_brain: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_USE_META_BRAIN", False)
    )
    use_exec_controller: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_USE_EXEC_CONTROLLER", False)
    )
    use_drift_monitor: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_USE_DRIFT_MONITOR", False)
    )
    use_sdr_prefilter: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_USE_SDR_PREFILTER", False)
    )
    use_graph_augment: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_USE_GRAPH_AUGMENT", False)
    )
    use_hrr_first: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_USE_HRR_FIRST", False)
    )

    # Graph configuration
    graph_hops: int = Field(
        default_factory=lambda: _int_env(
            "SOMABRAIN_GRAPH_HOPS", _yaml_get("graph_hops", 2)
        )
    )
    graph_limit: int = Field(
        default_factory=lambda: _int_env(
            "SOMABRAIN_GRAPH_LIMIT", _yaml_get("graph_limit", 20)
        )
    )
    graph_file: Optional[str] = Field(default=_str_env("SOMABRAIN_GRAPH_FILE"))
    graph_file_action: Optional[str] = Field(
        default=_str_env("SOMABRAIN_GRAPH_FILE_ACTION")
    )
    graph_file_agent: Optional[str] = Field(
        default=_str_env("SOMABRAIN_GRAPH_FILE_AGENT")
    )

    # Planner / graph walk
    planner_rwr_steps: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_PLANNER_RWR_STEPS", 20)
    )
    planner_rwr_restart: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_PLANNER_RWR_RESTART", 0.15)
    )
    planner_rwr_max_nodes: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_PLANNER_RWR_MAX_NODES", 128)
    )
    planner_rwr_edges_per_node: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_PLANNER_RWR_EDGES_PER_NODE", 32)
    )
    planner_rwr_max_items: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_PLANNER_RWR_MAX_ITEMS", 5)
    )

    # Rate limiting
    rate_rps: int = Field(default_factory=lambda: _int_env("SOMABRAIN_RATE_RPS", 1000))
    rate_burst: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_RATE_BURST", 2000)
    )
    write_daily_limit: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_WRITE_DAILY_LIMIT", 100000)
    )
