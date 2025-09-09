"""
Configuration Module for SomaBrain.

This module defines the configuration system for SomaBrain, providing centralized
control over all system parameters and feature flags. It supports loading configuration
from YAML files and environment variables using Dynaconf, with sensible defaults.

Key Features:
- Comprehensive configuration for all SomaBrain components
- Dynaconf integration for flexible configuration loading
- Environment variable support with ``SOMABRAIN_`` prefix
- Type-safe configuration with dataclasses
- Feature flags for optional components

Classes:
    MemoryHTTPConfig: Configuration for HTTP-based memory backends.
    Config: Main configuration class with all system parameters.

Functions:
    load_config: Load configuration from files and environment variables.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

try:
    from dynaconf import Dynaconf  # type: ignore
except Exception:

    class Dynaconf:  # minimal fallback
        def __init__(self, *_, **__):
            pass

        def __getattr__(self, _):
            return None


@dataclass
class MemoryHTTPConfig:
    """
    Configuration for HTTP-based memory backends.

    Defines connection parameters for remote memory services accessed via HTTP.

    Attributes:
        endpoint (Optional[str]): HTTP endpoint URL for the memory service.
        token (Optional[str]): Authentication token for the memory service.

    Example:
        >>> http_config = MemoryHTTPConfig(
        ...     endpoint="https://api.memory.example.com",
        ...     token="your-api-token"
        ... )
    """

    endpoint: Optional[str] = None
    token: Optional[str] = None


@dataclass
class Config:
    """
    Main configuration class for SomaBrain system.

    Comprehensive configuration container with parameters for all SomaBrain components
    including memory, embeddings, salience, neuromodulators, and various optional features.

    The configuration is organized into logical groups:
    - Memory and embeddings settings
    - Salience and attention parameters
    - Rate limiting and security
    - Reflection and consolidation
    - Graph reasoning and planning
    - Advanced features and optimizations

    Attributes:
        # Memory and Embeddings
        wm_size (int): Working memory buffer size. Default 64.
        embed_dim (int): Embedding vector dimensionality. Default 256.
        embed_provider (str): Embedding provider ("tiny", "transformer", "hrr"). Default "tiny".
        embed_model (Optional[str]): Specific model name for embedding provider.
        embed_dim_target_k (Optional[int]): Target dimension for dimension reduction.
        embed_cache_size (int): Size of embedding cache. Default 0.
        use_hrr (bool): Enable Holographic Reduced Representations. Default False.
        use_hrr_cleanup (bool): Enable HRR cleanup operations. Default False.
        hrr_dim (int): HRR vector dimensionality. Default 8192.
        hrr_seed (int): Random seed for HRR generation. Default 42.
        hrr_anchors_max (int): Maximum number of HRR anchors. Default 10000.

        # Salience and Attention
        salience_w_novelty (float): Weight for novelty in salience calculation. Default 0.6.
        salience_w_error (float): Weight for prediction error in salience. Default 0.4.
        salience_threshold_store (float): Threshold for storing memories. Default 0.5.
        salience_threshold_act (float): Threshold for taking actions. Default 0.7.
        salience_hysteresis (float): Hysteresis for salience thresholds. Default 0.05.

        # Memory Backend
        memory_mode (str): Memory backend mode ("local", "http", "stub"). Default "local".
        namespace (str): Memory namespace identifier. Default "somabrain_ns".
        http (MemoryHTTPConfig): HTTP memory configuration.

        # Security and Limits
        api_token (Optional[str]): API authentication token.
        rate_rps (float): Rate limit in requests per second. Default 50.0.
        rate_burst (int): Rate limit burst size. Default 100.
        write_daily_limit (int): Daily write operation limit. Default 10000.

        # Reflection System
        reflect_similarity_threshold (float): Similarity threshold for clustering. Default 0.35.
        reflect_min_cluster_size (int): Minimum cluster size for grouping. Default 2.
        reflect_max_summaries (int): Maximum summaries per reflection cycle. Default 5.

        # Graph Reasoning
        use_graph_augment (bool): Enable graph augmentation. Default False.
        graph_hops (int): Number of graph hops for reasoning. Default 1.
        graph_limit (int): Maximum graph nodes to consider. Default 20.
        graph_augment_max_additions (int): Max nodes to add via augmentation. Default 20.

        # Prediction and Learning
        predictor_provider (str): Prediction service provider. Default "stub".
        predictor_timeout_ms (int): Prediction timeout in milliseconds. Default 250.
        predictor_fail_degrade (bool): Degrade gracefully on prediction failure. Default True.

        # Authentication
        auth_required (bool): Require authentication for API access. Default False.

        # Consolidation and Sleep
        consolidation_enabled (bool): Enable memory consolidation. Default False.
        sleep_interval_seconds (int): Sleep cycle interval. Default 0.
        nrem_batch_size (int): Batch size for NREM consolidation. Default 16.
        rem_recomb_rate (float): Recombination rate for REM sleep. Default 0.2.
        max_summaries_per_cycle (int): Maximum summaries per consolidation cycle. Default 3.

        # Advanced Features
        use_soft_salience (bool): Enable soft salience calculation. Default False.
        soft_salience_temperature (float): Temperature for soft salience. Default 0.15.
        use_meta_brain (bool): Enable meta-brain functionality. Default False.
        meta_gain (float): Meta-brain proportional gain. Default 0.2.
        meta_limit (float): Meta-brain adjustment limit. Default 0.1.

        # Executive Controller
        use_exec_controller (bool): Enable executive controller. Default False.
        exec_window (int): Executive control window size. Default 8.
        exec_conflict_threshold (float): Threshold for conflict detection. Default 0.7.
        exec_explore_boost_k (int): Exploration boost factor. Default 2.
        exec_switch_threshold (float): Threshold for context switching. Default 0.85.
        exec_switch_universe (str): Universe for context switching. Default "cf:alt".
        exec_use_bandits (bool): Use bandit algorithms for exploration. Default False.
        exec_bandit_eps (float): Epsilon for epsilon-greedy bandits. Default 0.1.

        # Planning
        use_planner (bool): Enable planning functionality. Default False.
        plan_max_steps (int): Maximum planning steps. Default 5.
        plan_rel_types (str): Comma-separated relation types for planning. Default "depends_on,causes,part_of,motivates,related".

        # Microcircuits
        use_microcircuits (bool): Enable microcircuit processing. Default False.
        micro_circuits (int): Number of microcircuits. Default 1.
        micro_vote_temperature (float): Temperature for microcircuit voting. Default 0.25.

        # HRR Retrieval
        use_hrr_first (bool): Use HRR for first-stage retrieval. Default False.
        hrr_rerank_weight (float): Weight for HRR reranking. Default 0.3.
        hrr_rerank_only_low_margin (bool): Rerank only low-margin results. Default False.
        rerank_margin_threshold (float): Margin threshold for reranking. Default 0.05.

        # FDE/Muvera
        fde_enabled (bool): Enable FDE processing. Default False.
        fde_pooling (str): Pooling method for FDE. Default "gated_max".
        fde_margin_threshold (float): Margin threshold for FDE. Default 0.1.

        # Index Optimization
        index_profile (str): Index performance profile. Default "balanced".
        pq_m (int): Product quantization M parameter. Default 16.
        pq_bits (int): Product quantization bits. Default 8.
        opq_enabled (bool): Enable Optimized Product Quantization. Default False.
        anisotropic_enabled (bool): Enable anisotropic optimization. Default False.
        imi_cells (int): Inverted Multi-Index cells. Default 2048.
        hnsw_M (int): HNSW M parameter. Default 16.
        hnsw_efc (int): HNSW ef_construction parameter. Default 100.
        hnsw_efs (int): HNSW ef_search parameter. Default 64.

        # Diversity
        use_diversity (bool): Enable diversity reranking. Default False.
        diversity_method (str): Diversity method ("mmr", "facility"). Default "mmr".
        diversity_k (int): Diversity parameter k. Default 10.
        diversity_lambda (float): Diversity lambda parameter. Default 0.5.

        # Adaptive Salience
        use_adaptive_salience (bool): Enable adaptive salience. Default False.
        salience_target_store_rate (float): Target storage rate. Default 0.2.
        salience_target_act_rate (float): Target action rate. Default 0.1.
        salience_adjust_step (float): Adjustment step size. Default 0.01.

        # Link Maintenance
        link_decay_factor (float): Link decay factor. Default 0.98.
        link_min_weight (float): Minimum link weight. Default 0.05.

        # Provenance
        require_provenance (bool): Require provenance tracking. Default False.
        provenance_secret (Optional[str]): Secret for provenance verification.
        provenance_strict_deny (bool): Strict denial on provenance failure. Default False.

        # Drift Monitoring
        use_drift_monitor (bool): Enable drift monitoring. Default False.
        drift_window (int): Drift monitoring window size. Default 128.
        drift_threshold (float): Drift detection threshold. Default 5.0.

        # SDR Prefilter
        use_sdr_prefilter (bool): Enable SDR prefiltering. Default False.
        sdr_dim (int): SDR dimensionality. Default 16384.
        sdr_density (float): SDR density. Default 0.01.
        sdr_bands (int): Number of SDR bands. Default 8.
        sdr_rows (int): Number of rows per SDR band. Default 16.

        # ACC Lessons
        use_acc_lessons (bool): Enable ACC lessons. Default False.
        acc_error_threshold (float): Error threshold for ACC lessons. Default 0.8.

        # Demo Endpoints
        expose_alt_memory_endpoints (bool): Expose alternative memory endpoints. Default False.
        expose_brain_demos (bool): Expose brain demo endpoints. Default False.

        # Persistence
        persistent_journal_enabled (bool): Enable persistent journaling. Default False.
        journal_dir (str): Directory for journal files. Default "./data/somabrain".

    Example:
        >>> config = Config(
        ...     wm_size=128,
        ...     embed_dim=512,
        ...     memory_mode="http"
        ... )
    """

    wm_size: int = 64
    embed_dim: int = 256
    embed_provider: str = "tiny"  # tiny | transformer | hrr
    embed_model: Optional[str] = None
    embed_dim_target_k: Optional[int] = None
    embed_cache_size: int = 0
    use_hrr: bool = False
    use_hrr_cleanup: bool = False
    hrr_dim: int = 8192
    hrr_seed: int = 42
    hrr_anchors_max: int = 10000
    salience_w_novelty: float = 0.6
    salience_w_error: float = 0.4
    salience_threshold_store: float = 0.5
    salience_threshold_act: float = 0.7
    salience_hysteresis: float = 0.05
    memory_mode: str = "local"  # local | http | stub
    namespace: str = "somabrain_ns"
    http: MemoryHTTPConfig = None  # type: ignore
    api_token: Optional[str] = None
    rate_rps: float = 50.0
    rate_burst: int = 100
    write_daily_limit: int = 10000
    # Reflection
    reflect_similarity_threshold: float = 0.35
    reflect_min_cluster_size: int = 2
    reflect_max_summaries: int = 5
    # Graph reasoning
    use_graph_augment: bool = False
    graph_hops: int = 1
    graph_limit: int = 20
    graph_augment_max_additions: int = 20
    # Predictor provider
    predictor_provider: str = "stub"  # stub | slow (test)
    predictor_timeout_ms: int = 250
    predictor_fail_degrade: bool = True
    # Auth
    auth_required: bool = False
    # Consolidation / Sleep
    consolidation_enabled: bool = False
    sleep_interval_seconds: int = 0
    nrem_batch_size: int = 16
    rem_recomb_rate: float = 0.2
    max_summaries_per_cycle: int = 3
    # Soft Salience + Supervisor
    use_soft_salience: bool = False
    soft_salience_temperature: float = 0.15
    use_meta_brain: bool = False
    meta_gain: float = 0.2
    meta_limit: float = 0.1
    # Executive Controller
    use_exec_controller: bool = False
    exec_window: int = 8
    exec_conflict_threshold: float = 0.7
    exec_explore_boost_k: int = 2
    exec_switch_threshold: float = 0.85
    exec_switch_universe: str = "cf:alt"
    exec_use_bandits: bool = False
    exec_bandit_eps: float = 0.1
    # Planner
    use_planner: bool = False
    plan_max_steps: int = 5
    plan_rel_types: str = "depends_on,causes,part_of,motivates,related"
    # Microcircuits
    use_microcircuits: bool = False
    micro_circuits: int = 1
    micro_vote_temperature: float = 0.25
    # HRR-first retrieval
    use_hrr_first: bool = False
    hrr_rerank_weight: float = 0.3
    hrr_rerank_only_low_margin: bool = False
    rerank_margin_threshold: float = 0.05
    # MUVERA / FDE (placeholders)
    fde_enabled: bool = False
    fde_pooling: str = "gated_max"  # gated_max | attention
    fde_margin_threshold: float = 0.1
    # Index profiles and compression (placeholders for backend integration)
    index_profile: str = "balanced"  # low_latency | balanced | high_recall
    pq_m: int = 16
    pq_bits: int = 8
    opq_enabled: bool = False
    anisotropic_enabled: bool = False
    imi_cells: int = 2_048
    hnsw_M: int = 16
    hnsw_efc: int = 100
    hnsw_efs: int = 64
    # Diversity re-ranking (optional)
    use_diversity: bool = False
    diversity_method: str = "mmr"  # mmr | facility
    diversity_k: int = 10
    diversity_lambda: float = 0.5
    # Adaptive salience (optional)
    use_adaptive_salience: bool = False
    salience_target_store_rate: float = 0.2
    salience_target_act_rate: float = 0.1
    salience_adjust_step: float = 0.01
    # Link decay (graph maintenance)
    link_decay_factor: float = 0.98
    link_min_weight: float = 0.05
    # Memory coordinate/linking preference: if True, prefer server-returned coords for links
    prefer_server_coords_for_links: bool = False
    # Controls / Provenance
    require_provenance: bool = False
    provenance_secret: Optional[str] = None
    provenance_strict_deny: bool = False
    # Drift monitor
    use_drift_monitor: bool = False
    drift_window: int = 128
    drift_threshold: float = 5.0
    # SDR + LSH prefilter
    use_sdr_prefilter: bool = False
    sdr_dim: int = 16384
    sdr_density: float = 0.01
    sdr_bands: int = 8
    sdr_rows: int = 16
    # ACC Lessons (semantic corrections)
    use_acc_lessons: bool = False
    acc_error_threshold: float = 0.8
    # Demo endpoints (FNOM/Fractal/Unified Brain)
    expose_alt_memory_endpoints: bool = False
    expose_brain_demos: bool = False
    # Persistence (journaling for stub/local degraded mode)
    persistent_journal_enabled: bool = False
    journal_dir: str = "./data/somabrain"
    # Public API surface
    minimal_public_api: bool = True


def _load_config_legacy() -> Config:
    """Legacy config loader kept for reference; not used at runtime."""
    dc = None  # placeholder to satisfy static analysis (legacy stub)
    """
    Load configuration from YAML files and environment variables.

    Loads configuration using Dynaconf from config.yaml and environment variables
    with the SOMABRAIN_ prefix. Provides fallback defaults and graceful degradation
    when Dynaconf is not available.

    Returns:
        Config: Fully populated configuration object with all parameters set.

    Note:
        - Looks for config.yaml in the current directory
        - Environment variables override file settings
        - Falls back to sensible defaults if configuration sources are unavailable
        - Supports both SOMABRAIN_* and legacy environment variable names

    Example:
        >>> config = load_config()
        >>> print(f"Working memory size: {config.wm_size}")
    """
    dc = Dynaconf(
        settings_files=["config.yaml"], environments=True, envvar_prefix="SOMABRAIN"
    )
    http = MemoryHTTPConfig(
        endpoint=getattr(dc, "memory_http_endpoint", None)
        or getattr(dc, "HTTP_ENDPOINT", None),
        token=getattr(dc, "memory_http_token", None) or getattr(dc, "HTTP_TOKEN", None),
    )
    cfg = Config(
        wm_size=int(getattr(dc, "wm_size", 64) or 64),
        embed_dim=int(getattr(dc, "embed_dim", 256) or 256),
        embed_provider=str(
            getattr(dc, "embed_provider", getattr(dc, "EMBED_PROVIDER", "tiny"))
            or "tiny"
        ).lower(),
        embed_model=getattr(dc, "embed_model", None)
        or getattr(dc, "EMBED_MODEL", None),
        embed_dim_target_k=(int(getattr(dc, "embed_dim_target_k", 0) or 0) or None),
        embed_cache_size=int(getattr(dc, "embed_cache_size", 0) or 0),
        use_hrr=bool(getattr(dc, "use_hrr", False) or False),
        use_hrr_cleanup=bool(getattr(dc, "use_hrr_cleanup", False) or False),
        hrr_dim=int(getattr(dc, "hrr_dim", 8192) or 8192),
        hrr_seed=int(getattr(dc, "hrr_seed", 42) or 42),
        hrr_anchors_max=int(getattr(dc, "hrr_anchors_max", 10000) or 10000),
        salience_w_novelty=float(getattr(dc, "salience_w_novelty", 0.6) or 0.6),
        salience_w_error=float(getattr(dc, "salience_w_error", 0.4) or 0.4),
        salience_threshold_store=float(
            getattr(dc, "salience_threshold_store", 0.5) or 0.5
        ),
        salience_threshold_act=float(getattr(dc, "salience_threshold_act", 0.7) or 0.7),
        salience_hysteresis=float(getattr(dc, "salience_hysteresis", 0.05) or 0.05),
        memory_mode=(getattr(dc, "memory_mode", "local") or "local").lower(),
        namespace=str(getattr(dc, "namespace", "somabrain_ns") or "somabrain_ns"),
    )
    cfg.http = http
    # minimal public api
    try:
        cfg.minimal_public_api = bool(getattr(dc, "minimal_public_api", True))
    except Exception:
        pass
    # security/limits and optional features
    try:
        cfg.rate_rps = float(getattr(dc, "rate_rps", 50.0) or 50.0)
        cfg.rate_burst = int(getattr(dc, "rate_burst", 100) or 100)
        cfg.write_daily_limit = int(getattr(dc, "write_daily_limit", 10000) or 10000)
        cfg.reflect_similarity_threshold = float(
            getattr(dc, "reflect_similarity_threshold", 0.35) or 0.35
        )
        cfg.reflect_min_cluster_size = int(
            getattr(dc, "reflect_min_cluster_size", 2) or 2
        )
        cfg.reflect_max_summaries = int(getattr(dc, "reflect_max_summaries", 5) or 5)
        cfg.use_graph_augment = bool(getattr(dc, "use_graph_augment", False) or False)
        cfg.graph_hops = int(getattr(dc, "graph_hops", 1) or 1)
        cfg.graph_limit = int(getattr(dc, "graph_limit", 20) or 20)
        cfg.graph_augment_max_additions = int(
            getattr(dc, "graph_augment_max_additions", 20) or 20
        )
        cfg.predictor_provider = str(
            getattr(dc, "predictor_provider", "stub") or "stub"
        ).lower()
        cfg.predictor_timeout_ms = int(getattr(dc, "predictor_timeout_ms", 250) or 250)
        cfg.predictor_fail_degrade = bool(
            getattr(dc, "predictor_fail_degrade", True) or True
        )
        cfg.auth_required = bool(getattr(dc, "auth_required", False) or False)
        cfg.consolidation_enabled = bool(
            getattr(dc, "consolidation_enabled", False) or False
        )
        cfg.sleep_interval_seconds = int(getattr(dc, "sleep_interval_seconds", 0) or 0)
        cfg.nrem_batch_size = int(getattr(dc, "nrem_batch_size", 16) or 16)
        cfg.rem_recomb_rate = float(getattr(dc, "rem_recomb_rate", 0.2) or 0.2)
        cfg.max_summaries_per_cycle = int(
            getattr(dc, "max_summaries_per_cycle", 3) or 3
        )
        cfg.use_soft_salience = bool(getattr(dc, "use_soft_salience", False) or False)
        cfg.soft_salience_temperature = float(
            getattr(dc, "soft_salience_temperature", 0.15) or 0.15
        )
        cfg.use_meta_brain = bool(getattr(dc, "use_meta_brain", False) or False)
        cfg.meta_gain = float(getattr(dc, "meta_gain", 0.2) or 0.2)
        cfg.meta_limit = float(getattr(dc, "meta_limit", 0.1) or 0.1)
        cfg.use_exec_controller = bool(
            getattr(dc, "use_exec_controller", False) or False
        )
        cfg.exec_window = int(getattr(dc, "exec_window", 8) or 8)
        cfg.exec_conflict_threshold = float(
            getattr(dc, "exec_conflict_threshold", 0.7) or 0.7
        )
        cfg.exec_explore_boost_k = int(getattr(dc, "exec_explore_boost_k", 2) or 2)
        cfg.exec_switch_threshold = float(
            getattr(dc, "exec_switch_threshold", 0.85) or 0.85
        )
        cfg.exec_switch_universe = str(
            getattr(dc, "exec_switch_universe", "cf:alt") or "cf:alt"
        )
        cfg.exec_use_bandits = bool(getattr(dc, "exec_use_bandits", False) or False)
        cfg.exec_bandit_eps = float(getattr(dc, "exec_bandit_eps", 0.1) or 0.1)
        cfg.use_planner = bool(getattr(dc, "use_planner", False) or False)
        cfg.plan_max_steps = int(getattr(dc, "plan_max_steps", 5) or 5)
        cfg.plan_rel_types = str(
            getattr(dc, "plan_rel_types", "depends_on,causes,part_of,motivates,related")
            or "depends_on,causes,part_of,motivates,related"
        )
        cfg.use_microcircuits = bool(getattr(dc, "use_microcircuits", False) or False)
        cfg.micro_circuits = int(getattr(dc, "micro_circuits", 1) or 1)
        cfg.micro_vote_temperature = float(
            getattr(dc, "micro_vote_temperature", 0.25) or 0.25
        )
        cfg.use_hrr_first = bool(getattr(dc, "use_hrr_first", False) or False)
        cfg.hrr_rerank_weight = float(getattr(dc, "hrr_rerank_weight", 0.3) or 0.3)
        cfg.hrr_rerank_only_low_margin = bool(
            getattr(dc, "hrr_rerank_only_low_margin", False) or False
        )
        cfg.rerank_margin_threshold = float(
            getattr(dc, "rerank_margin_threshold", 0.05) or 0.05
        )
        cfg.fde_enabled = bool(getattr(dc, "fde_enabled", False) or False)
        cfg.fde_pooling = str(getattr(dc, "fde_pooling", "gated_max") or "gated_max")
        cfg.fde_margin_threshold = float(
            getattr(dc, "fde_margin_threshold", 0.1) or 0.1
        )
        cfg.index_profile = str(
            getattr(dc, "index_profile", getattr(dc, "INDEX_PROFILE", "balanced"))
            or "balanced"
        ).lower()
        cfg.pq_m = int(getattr(dc, "pq_m", 16) or 16)
        cfg.pq_bits = int(getattr(dc, "pq_bits", 8) or 8)
        cfg.opq_enabled = bool(getattr(dc, "opq_enabled", False) or False)
        cfg.anisotropic_enabled = bool(
            getattr(dc, "anisotropic_enabled", False) or False
        )
        cfg.imi_cells = int(getattr(dc, "imi_cells", 2048) or 2048)
        cfg.hnsw_M = int(getattr(dc, "hnsw_M", 16) or 16)
        cfg.hnsw_efc = int(getattr(dc, "hnsw_efc", 100) or 100)
        cfg.hnsw_efs = int(getattr(dc, "hnsw_efs", 64) or 64)
        cfg.use_diversity = bool(getattr(dc, "use_diversity", False) or False)
        cfg.diversity_method = str(getattr(dc, "diversity_method", "mmr") or "mmr")
        cfg.diversity_k = int(getattr(dc, "diversity_k", 10) or 10)
        cfg.diversity_lambda = float(getattr(dc, "diversity_lambda", 0.5) or 0.5)
        cfg.use_adaptive_salience = bool(
            getattr(dc, "use_adaptive_salience", False) or False
        )
        cfg.salience_target_store_rate = float(
            getattr(dc, "salience_target_store_rate", 0.2) or 0.2
        )
        cfg.salience_target_act_rate = float(
            getattr(dc, "salience_target_act_rate", 0.1) or 0.1
        )
        cfg.salience_adjust_step = float(
            getattr(dc, "salience_adjust_step", 0.01) or 0.01
        )
        cfg.link_decay_factor = float(getattr(dc, "link_decay_factor", 0.98) or 0.98)
        cfg.link_min_weight = float(getattr(dc, "link_min_weight", 0.05) or 0.05)
        cfg.require_provenance = bool(getattr(dc, "require_provenance", False) or False)
        cfg.provenance_secret = getattr(dc, "provenance_secret", None) or getattr(
            dc, "PROVENANCE_SECRET", None
        )
        cfg.provenance_strict_deny = bool(
            getattr(dc, "provenance_strict_deny", False) or False
        )
        cfg.use_drift_monitor = bool(getattr(dc, "use_drift_monitor", False) or False)
        cfg.drift_window = int(getattr(dc, "drift_window", 128) or 128)
        cfg.drift_threshold = float(getattr(dc, "drift_threshold", 5.0) or 5.0)
        cfg.use_sdr_prefilter = bool(getattr(dc, "use_sdr_prefilter", False) or False)
        cfg.sdr_dim = int(getattr(dc, "sdr_dim", 16384) or 16384)
        cfg.sdr_density = float(getattr(dc, "sdr_density", 0.01) or 0.01)
        cfg.sdr_bands = int(getattr(dc, "sdr_bands", 8) or 8)
        cfg.sdr_rows = int(getattr(dc, "sdr_rows", 16) or 16)
        cfg.use_acc_lessons = bool(getattr(dc, "use_acc_lessons", False) or False)
        cfg.acc_error_threshold = float(getattr(dc, "acc_error_threshold", 0.8) or 0.8)
        cfg.expose_alt_memory_endpoints = bool(
            getattr(dc, "expose_alt_memory_endpoints", False) or False
        )
        cfg.expose_brain_demos = bool(getattr(dc, "expose_brain_demos", False) or False)
        cfg.persistent_journal_enabled = bool(
            getattr(dc, "persistent_journal_enabled", False) or False
        )
        cfg.journal_dir = str(
            getattr(dc, "journal_dir", "./data/somabrain") or "./data/somabrain"
        )
    except Exception:
        pass
    # Fallback to env var if dynaconf absent or key unset
    try:
        import os as _os

        # Minimal Public API via env
        m = (_os.getenv("SOMABRAIN_MINIMAL_PUBLIC_API", "").strip() or "").lower()
        if m in ("1", "true", "yes", "on"):
            cfg.minimal_public_api = True
        if m in ("0", "false", "no", "off"):
            cfg.minimal_public_api = False
        if not bool(cfg.use_drift_monitor):
            env_flag = (
                _os.getenv("SOMABRAIN_USE_DRIFT_MONITOR", "").strip() or ""
            ).lower()
            if env_flag in ("1", "true", "yes", "on"):  # enable via env
                cfg.use_drift_monitor = True
        # Optional overrides
        w = _os.getenv("SOMABRAIN_DRIFT_WINDOW", "").strip()
        if w:
            cfg.drift_window = int(w)
        th = _os.getenv("SOMABRAIN_DRIFT_THRESHOLD", "").strip()
        if th:
            cfg.drift_threshold = float(th)
        j_en = (
            _os.getenv("SOMABRAIN_PERSISTENT_JOURNAL_ENABLED", "").strip() or ""
        ).lower()
        if j_en in ("1", "true", "yes", "on"):
            cfg.persistent_journal_enabled = True
        jdir = _os.getenv("SOMABRAIN_JOURNAL_DIR", "").strip()
        if jdir:
            cfg.journal_dir = jdir
    except Exception:
        pass
    return cfg


def load_config() -> Config:
    """
    Load configuration from YAML files and environment variables.

    Loads configuration using Dynaconf from config.yaml and environment variables
    with the SOMABRAIN_ prefix. Provides fallback defaults and graceful degradation
    when Dynaconf is not available.

    Returns:
        Config: Fully populated configuration object with all parameters set.

    Note:
        - Looks for config.yaml in the current directory
        - Environment variables override file settings
        - Falls back to sensible defaults if configuration sources are unavailable
        - Supports both SOMABRAIN_* and legacy environment variable names

    Example:
        >>> config = load_config()
        >>> print(f"Working memory size: {config.wm_size}")
    """
    dc = Dynaconf(
        settings_files=["config.yaml"], environments=True, envvar_prefix="SOMABRAIN"
    )
    http = MemoryHTTPConfig(
        endpoint=getattr(dc, "memory_http_endpoint", None)
        or getattr(dc, "HTTP_ENDPOINT", None),
        token=getattr(dc, "memory_http_token", None) or getattr(dc, "HTTP_TOKEN", None),
    )
    cfg = Config(
        wm_size=int(getattr(dc, "wm_size", 64) or 64),
        embed_dim=int(getattr(dc, "embed_dim", 256) or 256),
        embed_provider=str(
            getattr(dc, "embed_provider", getattr(dc, "EMBED_PROVIDER", "tiny"))
            or "tiny"
        ).lower(),
        embed_model=getattr(dc, "embed_model", None)
        or getattr(dc, "EMBED_MODEL", None),
        embed_dim_target_k=(int(getattr(dc, "embed_dim_target_k", 0) or 0) or None),
        embed_cache_size=int(getattr(dc, "embed_cache_size", 0) or 0),
        use_hrr=bool(getattr(dc, "use_hrr", False) or False),
        use_hrr_cleanup=bool(getattr(dc, "use_hrr_cleanup", False) or False),
        hrr_dim=int(getattr(dc, "hrr_dim", 8192) or 8192),
        hrr_seed=int(getattr(dc, "hrr_seed", 42) or 42),
        hrr_anchors_max=int(getattr(dc, "hrr_anchors_max", 10000) or 10000),
        salience_w_novelty=float(getattr(dc, "salience_w_novelty", 0.6) or 0.6),
        salience_w_error=float(getattr(dc, "salience_w_error", 0.4) or 0.4),
        salience_threshold_store=float(
            getattr(dc, "salience_threshold_store", 0.5) or 0.5
        ),
        salience_threshold_act=float(getattr(dc, "salience_threshold_act", 0.7) or 0.7),
        salience_hysteresis=float(getattr(dc, "salience_hysteresis", 0.05) or 0.05),
        memory_mode=(getattr(dc, "memory_mode", "local") or "local").lower(),
        namespace=str(getattr(dc, "namespace", "somabrain_ns") or "somabrain_ns"),
    )
    cfg.http = http
    # security/limits
    cfg.api_token = getattr(dc, "api_token", None) or getattr(dc, "API_TOKEN", None)
    # minimal public api
    try:
        cfg.minimal_public_api = bool(getattr(dc, "minimal_public_api", True))
    except Exception:
        pass
    try:
        cfg.rate_rps = float(getattr(dc, "rate_rps", 50.0) or 50.0)
        cfg.rate_burst = int(getattr(dc, "rate_burst", 100) or 100)
        cfg.write_daily_limit = int(getattr(dc, "write_daily_limit", 10000) or 10000)
        cfg.reflect_similarity_threshold = float(
            getattr(dc, "reflect_similarity_threshold", 0.35) or 0.35
        )
        cfg.reflect_min_cluster_size = int(
            getattr(dc, "reflect_min_cluster_size", 2) or 2
        )
        cfg.reflect_max_summaries = int(getattr(dc, "reflect_max_summaries", 5) or 5)
        cfg.use_graph_augment = bool(getattr(dc, "use_graph_augment", False) or False)
        cfg.graph_hops = int(getattr(dc, "graph_hops", 1) or 1)
        cfg.graph_limit = int(getattr(dc, "graph_limit", 20) or 20)
        cfg.graph_augment_max_additions = int(
            getattr(dc, "graph_augment_max_additions", 20) or 20
        )
        cfg.predictor_provider = str(
            getattr(dc, "predictor_provider", "stub") or "stub"
        ).lower()
        cfg.predictor_timeout_ms = int(getattr(dc, "predictor_timeout_ms", 250) or 250)
        cfg.predictor_fail_degrade = bool(
            getattr(dc, "predictor_fail_degrade", True) or True
        )
        cfg.auth_required = bool(getattr(dc, "auth_required", False) or False)
        cfg.consolidation_enabled = bool(
            getattr(dc, "consolidation_enabled", False) or False
        )
        cfg.sleep_interval_seconds = int(getattr(dc, "sleep_interval_seconds", 0) or 0)
        cfg.nrem_batch_size = int(getattr(dc, "nrem_batch_size", 16) or 16)
        cfg.rem_recomb_rate = float(getattr(dc, "rem_recomb_rate", 0.2) or 0.2)
        cfg.max_summaries_per_cycle = int(
            getattr(dc, "max_summaries_per_cycle", 3) or 3
        )
        cfg.use_soft_salience = bool(getattr(dc, "use_soft_salience", False) or False)
        cfg.soft_salience_temperature = float(
            getattr(dc, "soft_salience_temperature", 0.15) or 0.15
        )
        cfg.use_meta_brain = bool(getattr(dc, "use_meta_brain", False) or False)
        cfg.meta_gain = float(getattr(dc, "meta_gain", 0.2) or 0.2)
        cfg.meta_limit = float(getattr(dc, "meta_limit", 0.1) or 0.1)
        cfg.use_exec_controller = bool(
            getattr(dc, "use_exec_controller", False) or False
        )
        cfg.exec_window = int(getattr(dc, "exec_window", 8) or 8)
        cfg.exec_conflict_threshold = float(
            getattr(dc, "exec_conflict_threshold", 0.7) or 0.7
        )
        cfg.exec_explore_boost_k = int(getattr(dc, "exec_explore_boost_k", 2) or 2)
        cfg.exec_switch_threshold = float(
            getattr(dc, "exec_switch_threshold", 0.85) or 0.85
        )
        cfg.exec_switch_universe = str(
            getattr(dc, "exec_switch_universe", "cf:alt") or "cf:alt"
        )
        cfg.exec_use_bandits = bool(getattr(dc, "exec_use_bandits", False) or False)
        cfg.exec_bandit_eps = float(getattr(dc, "exec_bandit_eps", 0.1) or 0.1)
        cfg.use_planner = bool(getattr(dc, "use_planner", False) or False)
        cfg.plan_max_steps = int(getattr(dc, "plan_max_steps", 5) or 5)
        cfg.plan_rel_types = str(
            getattr(dc, "plan_rel_types", "depends_on,causes,part_of,motivates,related")
            or "depends_on,causes,part_of,motivates,related"
        )
        cfg.use_microcircuits = bool(getattr(dc, "use_microcircuits", False) or False)
        cfg.micro_circuits = int(getattr(dc, "micro_circuits", 1) or 1)
        cfg.micro_vote_temperature = float(
            getattr(dc, "micro_vote_temperature", 0.25) or 0.25
        )
        cfg.use_hrr_first = bool(getattr(dc, "use_hrr_first", False) or False)
        cfg.hrr_rerank_weight = float(getattr(dc, "hrr_rerank_weight", 0.3) or 0.3)
        cfg.hrr_rerank_only_low_margin = bool(
            getattr(dc, "hrr_rerank_only_low_margin", False) or False
        )
        cfg.rerank_margin_threshold = float(
            getattr(dc, "rerank_margin_threshold", 0.05) or 0.05
        )
        cfg.fde_enabled = bool(getattr(dc, "fde_enabled", False) or False)
        cfg.fde_pooling = str(getattr(dc, "fde_pooling", "gated_max") or "gated_max")
        cfg.fde_margin_threshold = float(
            getattr(dc, "fde_margin_threshold", 0.1) or 0.1
        )
        cfg.index_profile = str(
            getattr(dc, "index_profile", getattr(dc, "INDEX_PROFILE", "balanced"))
            or "balanced"
        ).lower()
        cfg.pq_m = int(getattr(dc, "pq_m", 16) or 16)
        cfg.pq_bits = int(getattr(dc, "pq_bits", 8) or 8)
        cfg.opq_enabled = bool(getattr(dc, "opq_enabled", False) or False)
        cfg.anisotropic_enabled = bool(
            getattr(dc, "anisotropic_enabled", False) or False
        )
        cfg.imi_cells = int(getattr(dc, "imi_cells", 2048) or 2048)
        cfg.hnsw_M = int(getattr(dc, "hnsw_M", 16) or 16)
        cfg.hnsw_efc = int(getattr(dc, "hnsw_efc", 100) or 100)
        cfg.hnsw_efs = int(getattr(dc, "hnsw_efs", 64) or 64)
        cfg.use_diversity = bool(getattr(dc, "use_diversity", False) or False)
        cfg.diversity_method = str(getattr(dc, "diversity_method", "mmr") or "mmr")
        cfg.diversity_k = int(getattr(dc, "diversity_k", 10) or 10)
        cfg.diversity_lambda = float(getattr(dc, "diversity_lambda", 0.5) or 0.5)
        cfg.use_adaptive_salience = bool(
            getattr(dc, "use_adaptive_salience", False) or False
        )
        cfg.salience_target_store_rate = float(
            getattr(dc, "salience_target_store_rate", 0.2) or 0.2
        )
        cfg.salience_target_act_rate = float(
            getattr(dc, "salience_target_act_rate", 0.1) or 0.1
        )
        cfg.salience_adjust_step = float(
            getattr(dc, "salience_adjust_step", 0.01) or 0.01
        )
        cfg.link_decay_factor = float(getattr(dc, "link_decay_factor", 0.98) or 0.98)
        cfg.link_min_weight = float(getattr(dc, "link_min_weight", 0.05) or 0.05)
        cfg.require_provenance = bool(getattr(dc, "require_provenance", False) or False)
        cfg.provenance_secret = getattr(dc, "provenance_secret", None) or getattr(
            dc, "PROVENANCE_SECRET", None
        )
        cfg.provenance_strict_deny = bool(
            getattr(dc, "provenance_strict_deny", False) or False
        )
        cfg.use_drift_monitor = bool(getattr(dc, "use_drift_monitor", False) or False)
        cfg.drift_window = int(getattr(dc, "drift_window", 128) or 128)
        cfg.drift_threshold = float(getattr(dc, "drift_threshold", 5.0) or 5.0)
        cfg.use_sdr_prefilter = bool(getattr(dc, "use_sdr_prefilter", False) or False)
        cfg.sdr_dim = int(getattr(dc, "sdr_dim", 16384) or 16384)
        cfg.sdr_density = float(getattr(dc, "sdr_density", 0.01) or 0.01)
        cfg.sdr_bands = int(getattr(dc, "sdr_bands", 8) or 8)
        cfg.sdr_rows = int(getattr(dc, "sdr_rows", 16) or 16)
        cfg.use_acc_lessons = bool(getattr(dc, "use_acc_lessons", False) or False)
        cfg.acc_error_threshold = float(getattr(dc, "acc_error_threshold", 0.8) or 0.8)
        cfg.expose_alt_memory_endpoints = bool(
            getattr(dc, "expose_alt_memory_endpoints", False) or False
        )
        cfg.expose_brain_demos = bool(getattr(dc, "expose_brain_demos", False) or False)
        cfg.persistent_journal_enabled = bool(
            getattr(dc, "persistent_journal_enabled", False) or False
        )
        cfg.journal_dir = str(
            getattr(dc, "journal_dir", "./data/somabrain") or "./data/somabrain"
        )
    except Exception:
        pass
    # Fallback to env var if dynaconf absent or key unset
    try:
        import os as _os

        # Minimal Public API via env
        m = (_os.getenv("SOMABRAIN_MINIMAL_PUBLIC_API", "").strip() or "").lower()
        if m in ("1", "true", "yes", "on"):
            cfg.minimal_public_api = True
        if m in ("0", "false", "no", "off"):
            cfg.minimal_public_api = False
        if not bool(cfg.use_drift_monitor):
            env_flag = (
                _os.getenv("SOMABRAIN_USE_DRIFT_MONITOR", "").strip() or ""
            ).lower()
            if env_flag in ("1", "true", "yes", "on"):  # enable via env
                cfg.use_drift_monitor = True
        # Optional overrides
        w = _os.getenv("SOMABRAIN_DRIFT_WINDOW", "").strip()
        if w:
            cfg.drift_window = int(w)
        th = _os.getenv("SOMABRAIN_DRIFT_THRESHOLD", "").strip()
        if th:
            cfg.drift_threshold = float(th)
        j_en = (
            _os.getenv("SOMABRAIN_PERSISTENT_JOURNAL_ENABLED", "").strip() or ""
        ).lower()
        if j_en in ("1", "true", "yes", "on"):
            cfg.persistent_journal_enabled = True
        jdir = _os.getenv("SOMABRAIN_JOURNAL_DIR", "").strip()
        if jdir:
            cfg.journal_dir = jdir
    except Exception:
        pass
    return cfg
