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
        default_factory=lambda: _str_env("SOMABRAIN_HRR_VECTOR_FAMILY", "bhdc") or "bhdc",
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
