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

from dataclasses import dataclass, field  # add field import
from typing import List, Optional

# dynaconf is optional; we don't require it at runtime. Configuration is loaded
# via `load_config()` using dataclass defaults and a YAML + environment override.


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
    """

    # End of Config docstring
    # Core configuration fields (restored)
    wm_size: int = 64
    embed_dim: int = 256
    embed_provider: str = "tiny"
    embed_model: Optional[str] = None
    embed_dim_target_k: Optional[int] = None
    embed_cache_size: int = 0
    use_hrr: bool = False
    use_hrr_cleanup: bool = False
    hrr_dim: int = 8192
    hrr_seed: int = 42
    hrr_anchors_max: int = 10000

    # Salience and Attention
    salience_w_novelty: float = 0.6
    salience_w_error: float = 0.4
    salience_threshold_store: float = 0.5
    salience_threshold_act: float = 0.7
    salience_hysteresis: float = 0.05

    # Memory Backend
    # Runtime memory access is performed exclusively through the external HTTP
    # memory service. Legacy "memory_mode" toggles have been removed.
    namespace: str = "somabrain_ns"
    http: MemoryHTTPConfig = field(
        default_factory=lambda: MemoryHTTPConfig(endpoint="http://localhost:9595")
    )
    outbox_path: str = "./data/somabrain/outbox.jsonl"
    # Redis backend configuration (optional)
    # Redis connection string is now dynamically constructed from SOMABRAIN_REDIS_HOST and SOMABRAIN_REDIS_PORT
    redis_url: str = "redis://localhost:6379"

    # Security and Limits
    api_token: Optional[str] = None
    rate_rps: float = 50.0
    jwt_secret: Optional[str] = None
    jwt_public_key_path: Optional[str] = None
    jwt_issuer: Optional[str] = None
    jwt_audience: Optional[str] = None
    default_tenant: str = "sandbox"
    sandbox_tenants: List[str] = field(default_factory=list)
    sandbox_tenants_file: Optional[str] = None
    rate_burst: int = 100
    write_daily_limit: int = 10000
    # Predictor configuration (added)
    predictor_provider: str = "stub"  # stub|mahal|slow|llm
    predictor_timeout_ms: int = 250
    predictor_llm_endpoint: Optional[str] = None
    predictor_llm_token: Optional[str] = None
    # End of Config fields

    # Auth
    auth_required: bool = False

    # Consolidation / Sleep
    consolidation_enabled: bool = False
    sleep_interval_seconds: int = 0
    nrem_batch_size: int = 16
    rem_recomb_rate: float = 0.2
    max_summaries_per_cycle: int = 3

    # Soft Salience
    use_soft_salience: bool = False
    soft_salience_temperature: float = 0.15

    # Meta
    use_meta_brain: bool = False
    meta_gain: float = 0.2
    meta_limit: float = 0.1

    # Exec controller
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

    # HRR-first
    use_hrr_first: bool = False
    hrr_rerank_weight: float = 0.3
    hrr_rerank_only_low_margin: bool = False
    rerank_margin_threshold: float = 0.05

    # FDE placeholder
    fde_enabled: bool = False
    fde_pooling: str = "gated_max"
    fde_margin_threshold: float = 0.1

    # Index profile
    index_profile: str = "balanced"
    pq_m: int = 16
    pq_bits: int = 8
    opq_enabled: bool = False
    anisotropic_enabled: bool = False
    imi_cells: int = 2048
    hnsw_M: int = 16
    hnsw_efc: int = 100
    hnsw_efs: int = 64

    # Graph configuration (added defaults)
    graph_hops: int = 2  # number of hops for graph traversal
    graph_limit: int = 100  # max nodes to retrieve in graph queries
    graph_augment_max_additions: int = 20  # max extra payloads from graph augmentation

    # Diversity
    use_diversity: bool = False
    diversity_method: str = "mmr"
    diversity_k: int = 10
    diversity_lambda: float = 0.5

    # RAG fusion weights
    retriever_weight_vector: float = 1.0
    retriever_weight_wm: float = 1.0
    retriever_weight_graph: float = 1.0
    retriever_weight_lexical: float = 0.8

    # Reranker config
    reranker_provider: Optional[str] = None
    reranker_top_n: int = 50
    reranker_out_k: int = 10
    reranker_model: Optional[str] = None
    reranker_batch: int = 32

    # Query expansion
    use_query_expansion: bool = False
    query_expansion_variants: int = 0

    # Adaptive salience
    use_adaptive_salience: bool = False
    salience_target_store_rate: float = 0.2
    salience_target_act_rate: float = 0.1
    salience_adjust_step: float = 0.01

    # Link decay
    link_decay_factor: float = 0.98
    link_min_weight: float = 0.05
    prefer_server_coords_for_links: bool = False

    # Provenance
    require_provenance: bool = False
    provenance_secret: Optional[str] = None
    provenance_strict_deny: bool = False

    # Drift monitor
    use_drift_monitor: bool = False
    drift_window: int = 128
    drift_threshold: float = 5.0

    # SDR prefilter
    use_sdr_prefilter: bool = False
    sdr_dim: int = 16384
    sdr_density: float = 0.01
    sdr_bands: int = 8
    sdr_rows: int = 16

    # ACC lessons
    use_acc_lessons: bool = False
    acc_error_threshold: float = 0.8

    # Demo endpoints
    expose_alt_memory_endpoints: bool = False
    expose_brain_demos: bool = False

    # Persistence
    persistent_journal_enabled: bool = False
    journal_dir: str = "./data/somabrain"
    journal_redact_fields: list[str] = field(default_factory=list)

    # Public API
    minimal_public_api: bool = False

    # Enable planner and graph augment by default for full test coverage
    use_planner: bool = True
    use_graph_augment: bool = True
    use_microcircuits: bool = True


# Load configuration helper
def load_config() -> Config:
    """Load configuration from 'config.yaml' if present and environment variables.
    Returns a Config instance with values overridden by environment variables prefixed with SOMABRAIN_.
    """
    import os

    cfg = Config()
    # Load YAML if exists
    yaml_path = os.path.join(os.getcwd(), "config.yaml")
    if os.path.isfile(yaml_path):
        try:
            import yaml

            with open(yaml_path, "r") as f:
                data = yaml.safe_load(f) or {}
            for key, value in data.items():
                if hasattr(cfg, key):
                    setattr(cfg, key, value)
            http_cfg = data.get("http")
            if isinstance(http_cfg, dict):
                cfg.http.endpoint = http_cfg.get("endpoint", cfg.http.endpoint)
                cfg.http.token = http_cfg.get("token", cfg.http.token)
        except Exception:
            pass
    # Override with environment variables (SOMABRAIN_ prefix)
    prefix = "SOMABRAIN_"
    for env_key, env_val in os.environ.items():
        if not env_key.startswith(prefix):
            continue
        # Special-case HTTP nested config to honor SOMABRAIN_MEMORY_HTTP_* overrides.
        if env_key == "SOMABRAIN_MEMORY_HTTP_ENDPOINT":
            cfg.http.endpoint = env_val
            continue
        if env_key == "SOMABRAIN_MEMORY_HTTP_TOKEN":
            cfg.http.token = env_val
            continue

        attr = env_key[len(prefix) :].lower()
        if hasattr(cfg, attr):
            # Simple type conversion: try int, float, bool, else keep string
            current = getattr(cfg, attr)
            try:
                if isinstance(current, bool):
                    setattr(cfg, attr, env_val.lower() in ("1", "true", "yes"))
                elif isinstance(current, int):
                    setattr(cfg, attr, int(env_val))
                elif isinstance(current, float):
                    setattr(cfg, attr, float(env_val))
                elif isinstance(current, list):
                    values = [
                        item.strip() for item in env_val.split(",") if item.strip()
                    ]
                    setattr(cfg, attr, values)
                else:
                    setattr(cfg, attr, env_val)
            except Exception:
                setattr(cfg, attr, env_val)
    return cfg
