"""Cognitive settings for SomaBrain.

This module contains configuration for cognitive/mathematical components:
- HRR (Holographic Reduced Representation) parameters
- SDR (Sparse Distributed Representation) parameters
- Quantum layer configuration
- Working memory slots
- Context budget
- Determinism and seeding
"""

from __future__ import annotations

from common.config.settings.base import (
    BaseSettings,
    Field,
    _bool_env,
    _float_env,
    _int_env,
    _str_env,
)


class CognitiveSettingsMixin(BaseSettings):
    """Cognitive/mathematical component settings mixin.

    These settings were previously hardcoded in somabrain/nano_profile.py.
    Moving them here centralizes configuration and allows environment-based overrides.
    """

    # HRR (Holographic Reduced Representation) configuration
    hrr_dim: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_HRR_DIM", 8192),
        description="Global HRR dimensionality (production canonical default)",
    )
    hrr_dtype: str = Field(
        default_factory=lambda: _str_env("SOMABRAIN_HRR_DTYPE", "float32") or "float32",
        description="Global HRR dtype (must match everywhere)",
    )
    hrr_renorm: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_HRR_RENORM", True),
        description="Always unit-norm after every HRR operation",
    )
    hrr_vector_family: str = Field(
        default_factory=lambda: _str_env("SOMABRAIN_HRR_VECTOR_FAMILY", "bhdc")
        or "bhdc",
        description="Binary hypervectors with deterministic permutation binding",
    )

    # BHDC (Binary Hyperdimensional Computing) configuration
    bhdc_sparsity: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_BHDC_SPARSITY", 0.1),
        description="Fraction of active dimensions for role/payload vectors",
    )

    # SDR (Sparse Distributed Representation) configuration
    sdr_bits: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_SDR_BITS", 2048),
        description="Total number of bits in SDR",
    )
    sdr_density: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_SDR_DENSITY", 0.03),
        description="SDR sparsity density (~3%)",
    )
    sdr_dim: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_SDR_DIM", 16384),
        description="SDR encoder dimensionality (default 16384)",
    )
    sdr_sparsity: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_SDR_SPARSITY", 0.01),
        description="SDR encoder sparsity (default 1%)",
    )

    # Context configuration
    context_budget_tokens: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_CONTEXT_BUDGET_TOKENS", 2048),
        description="Maximum tokens for context budget",
    )

    # Superposition configuration
    max_superpose: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_MAX_SUPERPOSE", 32),
        description="Maximum number of vectors to superpose",
    )

    # Working memory slots (default, can be overridden per-tenant)
    default_wm_slots: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_DEFAULT_WM_SLOTS", 12),
        description="Default number of working memory slots",
    )

    # Determinism and seeding
    global_seed: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_GLOBAL_SEED", 42),
        description="Global seed for all HRR/quantum operations (reproducibility)",
    )
    determinism: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_DETERMINISM", True),
        description="Enable deterministic mode for reproducibility",
    )

    # Quotas (can be overridden per-tenant)
    quota_tenant: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_QUOTA_TENANT", 10000),
        description="Default tenant quota",
    )
    quota_tool: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_QUOTA_TOOL", 1000),
        description="Default tool quota",
    )
    quota_action: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_QUOTA_ACTION", 500),
        description="Default action quota",
    )

    # Quantum layer configuration (from quantum.py defaults)
    quantum_dim: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_QUANTUM_DIM", 2048),
        description="Quantum layer dimensionality",
    )
    quantum_sparsity: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_QUANTUM_SPARSITY", 0.1),
        description="Quantum layer sparsity",
    )

    # Executive controller configuration (from exec_controller.py defaults)
    exec_window: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_EXEC_WINDOW", 8),
        description="Executive controller window size",
    )
    exec_conflict_threshold: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_EXEC_CONFLICT_THRESHOLD", 0.7),
        description="Executive controller conflict threshold",
    )
    exec_bandit_eps: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_EXEC_BANDIT_EPS", 0.1),
        description="Executive controller bandit epsilon",
    )

    # Drift monitor configuration (from controls/drift_monitor.py defaults)
    drift_window: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_DRIFT_WINDOW", 128),
        description="Drift monitor window size",
    )
    drift_threshold: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_DRIFT_THRESHOLD", 5.0),
        description="Drift monitor threshold",
    )

    # Policy configuration (from controls/policy.py defaults)
    policy_safety_threshold: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_POLICY_SAFETY_THRESHOLD", 0.9),
        description="Policy safety threshold",
    )

    # Reflect configuration (from reflect.py defaults)
    reflect_sim_threshold: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_REFLECT_SIM_THRESHOLD", 0.35),
        description="Reflection similarity threshold",
    )
    reflect_min_cluster_size: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_REFLECT_MIN_CLUSTER_SIZE", 2),
        description="Minimum cluster size for reflection",
    )

    # Amygdala/salience configuration (from amygdala.py defaults)
    salience_soft_temperature: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_SALIENCE_SOFT_TEMPERATURE", 0.15),
        description="Soft salience temperature",
    )

    # Emotion model configuration (from cognitive/emotion.py)
    emotion_decay_rate: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_EMOTION_DECAY_RATE", 0.01),
        description="Emotion decay rate toward neutral baseline (0.0-1.0)",
    )

    # Validation limits (from middleware/validation.py)
    validation_max_text_length: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_VALIDATION_MAX_TEXT_LENGTH", 10000),
        description="Maximum text length for cognitive input validation",
    )
    validation_max_embedding_dim: int = Field(
        default_factory=lambda: _int_env(
            "SOMABRAIN_VALIDATION_MAX_EMBEDDING_DIM", 4096
        ),
        description="Maximum embedding dimension for validation",
    )
    validation_min_embedding_dim: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_VALIDATION_MIN_EMBEDDING_DIM", 64),
        description="Minimum embedding dimension for validation",
    )

    # Context planner configuration (from context/planner.py)
    planner_length_penalty_scale: float = Field(
        default_factory=lambda: _float_env(
            "SOMABRAIN_PLANNER_LENGTH_PENALTY_SCALE", 1024.0
        ),
        description="Scale factor for prompt length penalty in planner",
    )
    planner_memory_penalty_scale: float = Field(
        default_factory=lambda: _float_env(
            "SOMABRAIN_PLANNER_MEMORY_PENALTY_SCALE", 10.0
        ),
        description="Scale factor for memory count penalty in planner",
    )

    # ---------------------------------------------------------------------------
    # Unified Planning Kernel Settings (Requirements 5.1-5.11)
    # ---------------------------------------------------------------------------

    # Planning kernel enable flags
    use_planner: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_USE_PLANNER", False),
        description="Enable unified planning kernel",
    )
    use_focus_state: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_USE_FOCUS_STATE", True),
        description="Enable FocusState for working memory tracking",
    )

    # Planning configuration
    plan_max_steps: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_PLAN_MAX_STEPS", 5),
        description="Maximum planning steps to return",
    )
    planner_backend: str = Field(
        default_factory=lambda: _str_env("SOMABRAIN_PLANNER_BACKEND", "bfs") or "bfs",
        description="Planning backend: 'bfs' or 'rwr'",
    )
    plan_time_budget_ms: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_PLAN_TIME_BUDGET_MS", 50),
        description="Time budget for planning in milliseconds",
    )
    plan_max_options: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_PLAN_MAX_OPTIONS", 10),
        description="Maximum options to consider during planning",
    )
    plan_rel_types: str = Field(
        default_factory=lambda: _str_env("SOMABRAIN_PLAN_REL_TYPES", "") or "",
        description="Comma-separated list of relation types to follow (empty = all)",
    )

    # RWR (Random Walk with Restart) planner configuration
    planner_rwr_steps: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_PLANNER_RWR_STEPS", 20),
        description="Number of RWR power iterations",
    )
    planner_rwr_restart: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_PLANNER_RWR_RESTART", 0.15),
        description="RWR restart probability",
    )
    planner_rwr_max_nodes: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_PLANNER_RWR_MAX_NODES", 100),
        description="Maximum nodes in RWR local subgraph",
    )

    # FocusState configuration
    focus_decay_gamma: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_FOCUS_DECAY_GAMMA", 0.90),
        description="Exponential decay factor for focus state",
    )
    focus_persist: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_FOCUS_PERSIST", False),
        description="Persist focus snapshots to memory",
    )
    focus_links: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_FOCUS_LINKS", False),
        description="Create graph links between focus snapshots",
    )
    focus_admit_top_n: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_FOCUS_ADMIT_TOP_N", 4),
        description="Number of top recall hits to admit into focus",
    )
