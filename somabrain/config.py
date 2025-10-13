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
    Config: Main c  onfiguration class with all system parameters.

Functions:
    load_config: Load configuration from files and environment variables.
"""

from __future__ import annotations

from dataclasses import dataclass, field  # add field import
from typing import List, Optional, Any

try:
    # Shared BaseSettings instance exported from common/config.
    from common.config.settings import settings as shared_settings
except Exception:  # pragma: no cover - optional dependency in legacy layouts
    shared_settings = None

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
    # Consolidation time budget per phase (seconds); guards NREM/REM loops
    consolidation_timeout_s: float = 1.0

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

    # HybridBrain+ truth-budget integration (opt-in)
    hybrid_math_enabled: bool = False
    # Optional path to a YAML truth-budget spec (see docs/truth_budget_example.yaml)
    truth_budget_path: Optional[str] = None
    # Runtime-loaded truth budget (populated by load_config if path provided)
    truth_budget: Optional[dict] = None
    # Convenience runtime fields mapped from truth-budget (populated by loader)
    truth_bind_block_m: Optional[int] = None
    truth_wiener_lambda: Optional[float] = None
    truth_ev_target: Optional[float] = None
    truth_ev_max_r: Optional[int] = None
    truth_appr_eps: Optional[float] = None
    truth_chebyshev_K: Optional[int] = None
    truth_kernel_relerr: Optional[float] = None
    truth_sinkhorn_tol: Optional[float] = None


# Typed truth-budget schema (module-level so tests can import)
@dataclass
class TruthBudget:
    epsilon_total: float = 0.05
    # bind
    bind_block_size_m: int = 128
    bind_wiener_lambda: float = 1e-4
    # density / rho
    density_ev_target: float = 0.9
    density_max_r: int = 128
    # graph
    appr_eps: float = 1e-4
    # kernel / chebyshev
    chebyshev_order_K: int = 24
    chebyshev_relerr: float = 0.02
    # bridge
    sinkhorn_tol: float = 1e-3

    def to_dict(self) -> dict:
        return {
            "epsilon_total": self.epsilon_total,
            "bind": {
                "block_size_m": self.bind_block_size_m,
                "wiener_lambda": self.bind_wiener_lambda,
            },
            "rho": {"ev_target": self.density_ev_target, "max_r": self.density_max_r},
            "graph": {"appr_eps": self.appr_eps},
            "kernel": {
                "chebyshev_K": self.chebyshev_order_K,
                "rel_err": self.chebyshev_relerr,
            },
            "bridge": {"sinkhorn_tol": self.sinkhorn_tol},
        }


def _validate_and_map_truth_budget(cfg: Config, raw: dict) -> TruthBudget:
    """Validate a raw truth-budget dict and return a typed TruthBudget.

    This also maps conservative defaults and populates convenience `cfg.truth_*` fields.
    Does not raise on recoverable errors; upstream code may use strict validation later.
    """
    tb = TruthBudget()
    try:
        if not isinstance(raw, dict):
            raw = {}
        tb.epsilon_total = float(raw.get("epsilon_total", tb.epsilon_total))
        b = raw.get("bind", {}) or {}
        tb.bind_block_size_m = int(b.get("block_size_m", tb.bind_block_size_m))
        tb.bind_wiener_lambda = float(b.get("wiener_lambda", tb.bind_wiener_lambda))
        r = raw.get("rho", {}) or {}
        # support either 'r' or 'max_r' or 'ev_target'
        if "r" in r:
            tb.density_max_r = int(r.get("r", tb.density_max_r))
        else:
            tb.density_max_r = int(r.get("max_r", tb.density_max_r))
        tb.density_ev_target = float(r.get("ev_target", tb.density_ev_target))
        g = raw.get("graph", {}) or {}
        tb.appr_eps = float(g.get("appr_eps", tb.appr_eps))
        k = raw.get("kernel", {}) or {}
        # support either chebyshev_order or chebyshev_K naming
        tb.chebyshev_order_K = int(
            k.get("chebyshev_order", k.get("chebyshev_K", tb.chebyshev_order_K))
        )
        tb.chebyshev_relerr = float(
            k.get("relerr", k.get("rel_err", tb.chebyshev_relerr))
        )
        br = raw.get("bridge", {}) or {}
        tb.sinkhorn_tol = float(br.get("sinkhorn_tol", tb.sinkhorn_tol))
    except Exception:
        # best-effort: keep tb defaults on parse failure
        pass

    # populate cfg convenience fields
    try:
        cfg.truth_bind_block_m = tb.bind_block_size_m
        cfg.truth_wiener_lambda = tb.bind_wiener_lambda
        cfg.truth_ev_target = tb.density_ev_target
        cfg.truth_ev_max_r = tb.density_max_r
        cfg.truth_appr_eps = tb.appr_eps
        cfg.truth_chebyshev_K = tb.chebyshev_order_K
        cfg.truth_kernel_relerr = tb.chebyshev_relerr
        cfg.truth_sinkhorn_tol = tb.sinkhorn_tol
    except Exception:
        pass

    return tb


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

    if shared_settings is not None:
        # Promote shared infrastructure endpoints into the runtime config.
        try:
            if getattr(shared_settings, "redis_url", None):
                cfg.redis_url = str(shared_settings.redis_url)
        except Exception:
            pass
        try:
            endpoint = getattr(shared_settings, "memory_http_endpoint", None)
            if endpoint:
                cfg.http.endpoint = str(endpoint)
            token = getattr(shared_settings, "memory_http_token", None)
            if token:
                cfg.http.token = str(token)
        except Exception:
            pass
        try:
            if shared_settings.jwt_secret:
                cfg.jwt_secret = shared_settings.jwt_secret
                cfg.auth_required = True
            if shared_settings.jwt_public_key_path:
                cfg.jwt_public_key_path = str(shared_settings.jwt_public_key_path)
        except Exception:
            pass
        try:
            if shared_settings.postgres_dsn:
                # Consumers expect DSN via SOMABRAIN_POSTGRES_DSN env normally;
                # this mapping keeps parity while centralising the source.
                os.environ.setdefault(
                    "SOMABRAIN_POSTGRES_DSN", str(shared_settings.postgres_dsn)
                )
        except Exception:
            pass

    return cfg


def load_truth_budget(cfg: Config) -> None:
    """If cfg.truth_budget_path is set and readable, load YAML into cfg.truth_budget."""
    import os
    from dataclasses import dataclass

    # Define a small dataclass schema for runtime mapping (kept local to avoid import cycles)
    @dataclass
    class TruthBudget:
        epsilon_total: float = 0.05
        bind: dict = None
        rho: dict = None
        graph: dict = None
        kernel: dict = None
        bridge: dict = None

        def to_dict(self) -> dict:
            return {
                "epsilon_total": self.epsilon_total,
                "bind": self.bind or {},
                "rho": self.rho or {},
                "graph": self.graph or {},
                "kernel": self.kernel or {},
                "bridge": self.bridge or {},
            }

    path = getattr(cfg, "truth_budget_path", None)
    if not path:
        return
    if not os.path.isfile(path):
        return
    try:
        import yaml

        with open(path, "r") as f:
            raw = yaml.safe_load(f) or {}
        # Basic validation and mapping to typed structure
        tb = TruthBudget()
        if isinstance(raw, dict):
            tb.epsilon_total = float(raw.get("epsilon_total", tb.epsilon_total))
            tb.bind = raw.get("bind", {})
            tb.rho = raw.get("rho", {})
            tb.graph = raw.get("graph", {})
            tb.kernel = raw.get("kernel", {})
            tb.bridge = raw.get("bridge", {})
        data = tb.to_dict()
        cfg.truth_budget = data
        # Populate convenience runtime knobs with safe defaults and clamps
        # bind.block_size_m -> truth_bind_block_m
        try:
            b = data.get("bind", {})
            cfg.truth_bind_block_m = int(b.get("block_size_m", 128))
        except Exception:
            cfg.truth_bind_block_m = 128
        try:
            cfg.truth_wiener_lambda = float(b.get("wiener_lambda", 1e-4))
        except Exception:
            cfg.truth_wiener_lambda = 1e-4
        # rho: ev_target or r
        try:
            r = data.get("rho", {})
            cfg.truth_ev_target = float(r.get("ev_target", 0.9))
            cfg.truth_ev_max_r = int(r.get("max_r", 128))
        except Exception:
            cfg.truth_ev_target = 0.9
            cfg.truth_ev_max_r = 128
        # graph: appr_eps
        try:
            g = data.get("graph", {})
            cfg.truth_appr_eps = float(g.get("appr_eps", 1e-4))
        except Exception:
            cfg.truth_appr_eps = 1e-4
        # kernel: chebyshev K and relative error
        try:
            k = data.get("kernel", {})
            cfg.truth_chebyshev_K = int(k.get("chebyshev_K", 24))
            cfg.truth_kernel_relerr = float(k.get("rel_err", 0.02))
        except Exception:
            cfg.truth_chebyshev_K = 24
            cfg.truth_kernel_relerr = 0.02
        # bridge/sinkhorn tolerance
        try:
            br = data.get("bridge", {})
            cfg.truth_sinkhorn_tol = float(br.get("sinkhorn_tol", 1e-3))
        except Exception:
            cfg.truth_sinkhorn_tol = 1e-3
    except Exception:
        # best-effort; do not raise on parse failures here
        cfg.truth_budget = None


@dataclass
class _LocalTruthBudgetModel:
    """Internal helper schema for truth-budget parsing.

    Kept separate from the public TruthBudget to avoid class redefinition
    conflicts and make it clear we map into the public API before returning.
    """

    epsilon_total: float = 0.05
    bind_block_m: Optional[int] = None
    wiener_lambda: Optional[float] = None
    density_ev_target: Optional[float] = 0.9
    density_r: Optional[int] = None
    graph_appr_eps: Optional[float] = 1e-3
    chebyshev_order_K: Optional[int] = 24
    kernel_relerr: Optional[float] = 0.02
    sinkhorn_tol: Optional[float] = 1e-3


def _validate_and_map_truth_budget(
    cfg: Config, data: dict[str, Any]
) -> Optional[TruthBudget]:
    """Validate minimal truth-budget keys and map into Config-level knobs.

    Returns a TruthBudget instance or a TruthBudget with conservative defaults on parse error.
    """
    try:
        model = _LocalTruthBudgetModel(
            epsilon_total=float(data.get("epsilon_total", 0.05)),
            bind_block_m=(
                int(
                    data.get("bind", {}).get(
                        "block_size_m", data.get("bind", {}).get("block_m", 128)
                    )
                )
                or 128
            ),
            wiener_lambda=(
                float(data.get("bind", {}).get("wiener_lambda", 1e-4)) or 1e-4
            ),
            density_ev_target=(float(data.get("rho", {}).get("ev_target", 0.9)) or 0.9),
            density_r=(int(data.get("rho", {}).get("r", 128)) or 128),
            graph_appr_eps=(float(data.get("graph", {}).get("appr_eps", 1e-3)) or 1e-3),
            chebyshev_order_K=(
                int(
                    data.get("kernel", {}).get(
                        "chebyshev_order", data.get("kernel", {}).get("chebyshev_K", 24)
                    )
                )
                or 24
            ),
            kernel_relerr=(
                float(
                    data.get("kernel", {}).get(
                        "relerr", data.get("kernel", {}).get("rel_err", 0.02)
                    )
                )
                or 0.02
            ),
            sinkhorn_tol=(
                float(data.get("bridge", {}).get("sinkhorn_tol", 1e-3)) or 1e-3
            ),
        )
        # Sanity clamps
        if model.epsilon_total <= 0 or model.epsilon_total >= 1:
            model.epsilon_total = 0.05
        if model.density_ev_target is None or not (
            0.0 < model.density_ev_target <= 1.0
        ):
            model.density_ev_target = 0.9
        if model.bind_block_m is not None and model.bind_block_m < 8:
            model.bind_block_m = 8
        if model.chebyshev_order_K is not None and model.chebyshev_order_K < 4:
            model.chebyshev_order_K = 4

        # Map conservative defaults into cfg for runtime convenience (only set if not already set)
        if model.bind_block_m and not getattr(cfg, "truth_bind_block_m", None):
            setattr(cfg, "truth_bind_block_m", model.bind_block_m)
        if model.wiener_lambda and not getattr(cfg, "truth_wiener_lambda", None):
            setattr(cfg, "truth_wiener_lambda", model.wiener_lambda)
        if model.density_r and not getattr(cfg, "truth_density_r", None):
            setattr(cfg, "truth_density_r", model.density_r)
        if model.chebyshev_order_K and not getattr(cfg, "truth_chebyshev_K", None):
            setattr(cfg, "truth_chebyshev_K", model.chebyshev_order_K)
        if model.graph_appr_eps and not getattr(cfg, "truth_graph_appr_eps", None):
            setattr(cfg, "truth_graph_appr_eps", model.graph_appr_eps)
        if model.kernel_relerr and not getattr(cfg, "truth_kernel_relerr", None):
            setattr(cfg, "truth_kernel_relerr", model.kernel_relerr)
        if model.sinkhorn_tol and not getattr(cfg, "truth_sinkhorn_tol", None):
            setattr(cfg, "truth_sinkhorn_tol", model.sinkhorn_tol)
        # Return the public TruthBudget instance for tests/callers with correct field names
        tb_public = TruthBudget(
            epsilon_total=model.epsilon_total,
            bind_block_size_m=(
                model.bind_block_m
                if model.bind_block_m is not None
                else TruthBudget().bind_block_size_m
            ),
            bind_wiener_lambda=(
                model.wiener_lambda
                if model.wiener_lambda is not None
                else TruthBudget().bind_wiener_lambda
            ),
            density_ev_target=(
                model.density_ev_target
                if model.density_ev_target is not None
                else TruthBudget().density_ev_target
            ),
            density_max_r=(
                model.density_r
                if model.density_r is not None
                else TruthBudget().density_max_r
            ),
            appr_eps=(
                model.graph_appr_eps
                if model.graph_appr_eps is not None
                else TruthBudget().appr_eps
            ),
            chebyshev_order_K=(
                model.chebyshev_order_K
                if model.chebyshev_order_K is not None
                else TruthBudget().chebyshev_order_K
            ),
            chebyshev_relerr=(
                model.kernel_relerr
                if model.kernel_relerr is not None
                else TruthBudget().chebyshev_relerr
            ),
            sinkhorn_tol=(
                model.sinkhorn_tol
                if model.sinkhorn_tol is not None
                else TruthBudget().sinkhorn_tol
            ),
        )
        return tb_public
    except Exception:
        # On parse error, return conservative defaults instead of None
        return TruthBudget()


def load_config_and_truth() -> Config:
    """Helper that loads main config and attempts to load a truth-budget YAML if configured.

    This wraps `load_config()` for call sites that want the runtime truth budget loaded
    into the returned Config object.
    """
    cfg = load_config()
    # Best-effort: if truth_budget_path provided, attempt to load it and enable hybrid math
    try:
        load_truth_budget(cfg)
        if cfg.truth_budget and not cfg.hybrid_math_enabled:
            # If a truth budget is present, default to enabling hybrid math to honor the spec.
            cfg.hybrid_math_enabled = True
    except Exception:
        # swallow errors; leave cfg as-is
        pass
    return cfg
