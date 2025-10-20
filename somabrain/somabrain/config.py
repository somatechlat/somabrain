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
    endpoint: Optional[str] = None
    token: Optional[str] = None


@dataclass
class Config:
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


def load_config() -> Config:
    dc = Dynaconf(settings_files=["config.yaml"], environments=True, envvar_prefix="SOMABRAIN")
    http = MemoryHTTPConfig(
        endpoint=getattr(dc, "memory_http_endpoint", None) or getattr(dc, "HTTP_ENDPOINT", None),
        token=getattr(dc, "memory_http_token", None) or getattr(dc, "HTTP_TOKEN", None),
    )
    cfg = Config(
        wm_size=int(getattr(dc, "wm_size", 64) or 64),
        embed_dim=int(getattr(dc, "embed_dim", 256) or 256),
        embed_provider=str(getattr(dc, "embed_provider", getattr(dc, "EMBED_PROVIDER", "tiny")) or "tiny").lower(),
        embed_model=getattr(dc, "embed_model", None) or getattr(dc, "EMBED_MODEL", None),
        embed_dim_target_k=(int(getattr(dc, "embed_dim_target_k", 0) or 0) or None),
        embed_cache_size=int(getattr(dc, "embed_cache_size", 0) or 0),
        use_hrr=bool(getattr(dc, "use_hrr", False) or False),
        use_hrr_cleanup=bool(getattr(dc, "use_hrr_cleanup", False) or False),
        hrr_dim=int(getattr(dc, "hrr_dim", 8192) or 8192),
        hrr_seed=int(getattr(dc, "hrr_seed", 42) or 42),
        hrr_anchors_max=int(getattr(dc, "hrr_anchors_max", 10000) or 10000),
        salience_w_novelty=float(getattr(dc, "salience_w_novelty", 0.6) or 0.6),
        salience_w_error=float(getattr(dc, "salience_w_error", 0.4) or 0.4),
        salience_threshold_store=float(getattr(dc, "salience_threshold_store", 0.5) or 0.5),
        salience_threshold_act=float(getattr(dc, "salience_threshold_act", 0.7) or 0.7),
        salience_hysteresis=float(getattr(dc, "salience_hysteresis", 0.05) or 0.05),
        memory_mode=(getattr(dc, "memory_mode", "local") or "local").lower(),
        namespace=str(getattr(dc, "namespace", "somabrain_ns") or "somabrain_ns"),
    )
    cfg.http = http
    # security/limits
    cfg.api_token = getattr(dc, "api_token", None) or getattr(dc, "API_TOKEN", None)
    try:
        cfg.rate_rps = float(getattr(dc, "rate_rps", 50.0) or 50.0)
        cfg.rate_burst = int(getattr(dc, "rate_burst", 100) or 100)
        cfg.write_daily_limit = int(getattr(dc, "write_daily_limit", 10000) or 10000)
        cfg.reflect_similarity_threshold = float(getattr(dc, "reflect_similarity_threshold", 0.35) or 0.35)
        cfg.reflect_min_cluster_size = int(getattr(dc, "reflect_min_cluster_size", 2) or 2)
        cfg.reflect_max_summaries = int(getattr(dc, "reflect_max_summaries", 5) or 5)
        cfg.use_graph_augment = bool(getattr(dc, "use_graph_augment", False) or False)
        cfg.graph_hops = int(getattr(dc, "graph_hops", 1) or 1)
        cfg.graph_limit = int(getattr(dc, "graph_limit", 20) or 20)
        cfg.predictor_provider = str(getattr(dc, "predictor_provider", "stub") or "stub").lower()
        cfg.predictor_timeout_ms = int(getattr(dc, "predictor_timeout_ms", 250) or 250)
        cfg.predictor_fail_degrade = bool(getattr(dc, "predictor_fail_degrade", True) or True)
        cfg.auth_required = bool(getattr(dc, "auth_required", False) or False)
        cfg.consolidation_enabled = bool(getattr(dc, "consolidation_enabled", False) or False)
        cfg.sleep_interval_seconds = int(getattr(dc, "sleep_interval_seconds", 0) or 0)
        cfg.nrem_batch_size = int(getattr(dc, "nrem_batch_size", 16) or 16)
        cfg.rem_recomb_rate = float(getattr(dc, "rem_recomb_rate", 0.2) or 0.2)
        cfg.max_summaries_per_cycle = int(getattr(dc, "max_summaries_per_cycle", 3) or 3)
        cfg.use_soft_salience = bool(getattr(dc, "use_soft_salience", False) or False)
        cfg.soft_salience_temperature = float(getattr(dc, "soft_salience_temperature", 0.15) or 0.15)
        cfg.use_meta_brain = bool(getattr(dc, "use_meta_brain", False) or False)
        cfg.meta_gain = float(getattr(dc, "meta_gain", 0.2) or 0.2)
        cfg.meta_limit = float(getattr(dc, "meta_limit", 0.1) or 0.1)
        cfg.use_exec_controller = bool(getattr(dc, "use_exec_controller", False) or False)
        cfg.exec_window = int(getattr(dc, "exec_window", 8) or 8)
        cfg.exec_conflict_threshold = float(getattr(dc, "exec_conflict_threshold", 0.7) or 0.7)
        cfg.exec_explore_boost_k = int(getattr(dc, "exec_explore_boost_k", 2) or 2)
        cfg.exec_switch_threshold = float(getattr(dc, "exec_switch_threshold", 0.85) or 0.85)
        cfg.exec_switch_universe = str(getattr(dc, "exec_switch_universe", "cf:alt") or "cf:alt")
        cfg.exec_use_bandits = bool(getattr(dc, "exec_use_bandits", False) or False)
        cfg.exec_bandit_eps = float(getattr(dc, "exec_bandit_eps", 0.1) or 0.1)
        cfg.use_planner = bool(getattr(dc, "use_planner", False) or False)
        cfg.plan_max_steps = int(getattr(dc, "plan_max_steps", 5) or 5)
        cfg.plan_rel_types = str(getattr(dc, "plan_rel_types", "depends_on,causes,part_of,motivates,related") or "depends_on,causes,part_of,motivates,related")
        cfg.use_microcircuits = bool(getattr(dc, "use_microcircuits", False) or False)
        cfg.micro_circuits = int(getattr(dc, "micro_circuits", 1) or 1)
        cfg.micro_vote_temperature = float(getattr(dc, "micro_vote_temperature", 0.25) or 0.25)
        cfg.use_hrr_first = bool(getattr(dc, "use_hrr_first", False) or False)
        cfg.hrr_rerank_weight = float(getattr(dc, "hrr_rerank_weight", 0.3) or 0.3)
        cfg.hrr_rerank_only_low_margin = bool(getattr(dc, "hrr_rerank_only_low_margin", False) or False)
        cfg.rerank_margin_threshold = float(getattr(dc, "rerank_margin_threshold", 0.05) or 0.05)
        cfg.fde_enabled = bool(getattr(dc, "fde_enabled", False) or False)
        cfg.fde_pooling = str(getattr(dc, "fde_pooling", "gated_max") or "gated_max")
        cfg.fde_margin_threshold = float(getattr(dc, "fde_margin_threshold", 0.1) or 0.1)
        cfg.index_profile = str(getattr(dc, "index_profile", getattr(dc, "INDEX_PROFILE", "balanced")) or "balanced").lower()
        cfg.pq_m = int(getattr(dc, "pq_m", 16) or 16)
        cfg.pq_bits = int(getattr(dc, "pq_bits", 8) or 8)
        cfg.opq_enabled = bool(getattr(dc, "opq_enabled", False) or False)
        cfg.anisotropic_enabled = bool(getattr(dc, "anisotropic_enabled", False) or False)
        cfg.imi_cells = int(getattr(dc, "imi_cells", 2048) or 2048)
        cfg.hnsw_M = int(getattr(dc, "hnsw_M", 16) or 16)
        cfg.hnsw_efc = int(getattr(dc, "hnsw_efc", 100) or 100)
        cfg.hnsw_efs = int(getattr(dc, "hnsw_efs", 64) or 64)
        cfg.use_diversity = bool(getattr(dc, "use_diversity", False) or False)
        cfg.diversity_method = str(getattr(dc, "diversity_method", "mmr") or "mmr")
        cfg.diversity_k = int(getattr(dc, "diversity_k", 10) or 10)
        cfg.diversity_lambda = float(getattr(dc, "diversity_lambda", 0.5) or 0.5)
        cfg.use_adaptive_salience = bool(getattr(dc, "use_adaptive_salience", False) or False)
        cfg.salience_target_store_rate = float(getattr(dc, "salience_target_store_rate", 0.2) or 0.2)
        cfg.salience_target_act_rate = float(getattr(dc, "salience_target_act_rate", 0.1) or 0.1)
        cfg.salience_adjust_step = float(getattr(dc, "salience_adjust_step", 0.01) or 0.01)
        cfg.link_decay_factor = float(getattr(dc, "link_decay_factor", 0.98) or 0.98)
        cfg.link_min_weight = float(getattr(dc, "link_min_weight", 0.05) or 0.05)
        cfg.require_provenance = bool(getattr(dc, "require_provenance", False) or False)
        cfg.provenance_secret = getattr(dc, "provenance_secret", None) or getattr(dc, "PROVENANCE_SECRET", None)
        cfg.provenance_strict_deny = bool(getattr(dc, "provenance_strict_deny", False) or False)
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
    except Exception:
        pass
    return cfg
