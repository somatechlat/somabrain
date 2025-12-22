"""Learning and adaptation settings for SomaBrain.

This module contains configuration for:
- Adaptation engine parameters
- Tau annealing
- Entropy cap
- Neuromodulator settings
- Sleep/consolidation system
- Predictor configuration
- Segmentation parameters
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
)


class LearningSettingsMixin(BaseSettings):
    """Learning and adaptation settings mixin."""

    # Tau / entropy tuning
    tau_decay_enabled: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_TAU_DECAY_ENABLED", False)
    )
    tau_decay_rate: Optional[float] = Field(
        default=_float_env("SOMABRAIN_TAU_DECAY_RATE", 0.0)
    )
    tau_anneal_mode: Optional[str] = Field(
        default=_str_env("SOMABRAIN_TAU_ANNEAL_MODE")
    )
    tau_anneal_rate: Optional[float] = Field(
        default=_float_env("SOMABRAIN_TAU_ANNEAL_RATE", 0.0)
    )
    tau_anneal_step_interval: Optional[int] = Field(
        default=_int_env("SOMABRAIN_TAU_ANNEAL_STEP_INTERVAL", 0)
    )
    tau_min: Optional[float] = Field(default=_float_env("SOMABRAIN_TAU_MIN", 0.0))
    entropy_cap_enabled: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_ENTROPY_CAP_ENABLED", False)
    )
    entropy_cap: Optional[float] = Field(
        default=_float_env("SOMABRAIN_ENTROPY_CAP", 0.0)
    )
    enable_advanced_learning: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_ENABLE_ADVANCED_LEARNING", True)
    )
    learning_rate_dynamic: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_LEARNING_RATE_DYNAMIC", False)
    )

    # Learning tenant configuration
    learning_tenants_overrides: Optional[str] = Field(
        default=_str_env("SOMABRAIN_LEARNING_TENANTS_OVERRIDES")
    )
    learning_tenants_config: Optional[str] = Field(
        default=_str_env("LEARNING_TENANTS_CONFIG")
    )
    learning_tenants_file: Optional[str] = Field(
        default=_str_env("SOMABRAIN_LEARNING_TENANTS_FILE")
    )

    # Adaptation engine
    adaptation_learning_rate: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_ADAPT_LR", 0.05)
    )
    adaptation_max_history: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_ADAPT_MAX_HISTORY", 1000)
    )
    adaptation_alpha_min: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_ADAPT_ALPHA_MIN", 0.1)
    )
    adaptation_alpha_max: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_ADAPT_ALPHA_MAX", 5.0)
    )
    adaptation_gamma_min: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_ADAPT_GAMMA_MIN", 0.0)
    )
    adaptation_gamma_max: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_ADAPT_GAMMA_MAX", 1.0)
    )
    adaptation_lambda_min: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_ADAPT_LAMBDA_MIN", 0.1)
    )
    adaptation_lambda_max: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_ADAPT_LAMBDA_MAX", 5.0)
    )
    adaptation_mu_min: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_ADAPT_MU_MIN", 0.01)
    )
    adaptation_mu_max: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_ADAPT_MU_MAX", 5.0)
    )
    adaptation_nu_min: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_ADAPT_NU_MIN", 0.01)
    )
    adaptation_nu_max: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_ADAPT_NU_MAX", 5.0)
    )
    adaptation_gain_alpha: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_ADAPT_GAIN_ALPHA", 1.0)
    )
    adaptation_gain_gamma: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_ADAPT_GAIN_GAMMA", -0.5)
    )
    adaptation_gain_lambda: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_ADAPT_GAIN_LAMBDA", 1.0)
    )
    adaptation_gain_mu: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_ADAPT_GAIN_MU", -0.25)
    )
    adaptation_gain_nu: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_ADAPT_GAIN_NU", -0.25)
    )

    # Utility weights
    utility_lambda: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_UTILITY_LAMBDA", 1.0)
    )
    utility_mu: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_UTILITY_MU", 0.1)
    )
    utility_nu: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_UTILITY_NU", 0.05)
    )
    utility_lambda_min: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_UTILITY_LAMBDA_MIN", 0.0)
    )
    utility_lambda_max: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_UTILITY_LAMBDA_MAX", 5.0)
    )
    utility_mu_min: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_UTILITY_MU_MIN", 0.0)
    )
    utility_mu_max: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_UTILITY_MU_MAX", 5.0)
    )
    utility_nu_min: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_UTILITY_NU_MIN", 0.0)
    )
    utility_nu_max: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_UTILITY_NU_MAX", 5.0)
    )

    # Neuromodulator settings
    neuromod_dopamine_base: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_NEURO_DOPAMINE_BASE", 0.4)
    )
    neuromod_serotonin_base: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_NEURO_SEROTONIN_BASE", 0.5)
    )
    neuromod_noradrenaline_base: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_NEURO_NORAD_BASE", 0.0)
    )
    neuromod_acetylcholine_base: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_NEURO_ACETYL_BASE", 0.0)
    )
    neuromod_dopamine_min: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_NEURO_DOPAMINE_MIN", 0.1)
    )
    neuromod_dopamine_max: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_NEURO_DOPAMINE_MAX", 1.0)
    )
    neuromod_serotonin_min: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_NEURO_SEROTONIN_MIN", 0.0)
    )
    neuromod_serotonin_max: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_NEURO_SEROTONIN_MAX", 1.0)
    )
    neuromod_noradrenaline_min: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_NEURO_NORAD_MIN", 0.0)
    )
    neuromod_noradrenaline_max: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_NEURO_NORAD_MAX", 0.5)
    )
    neuromod_acetylcholine_min: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_NEURO_ACETYL_MIN", 0.0)
    )
    neuromod_acetylcholine_max: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_NEURO_ACETYL_MAX", 0.5)
    )
    neuromod_dopamine_lr: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_NEURO_DOPAMINE_LR", 0.02)
    )
    neuromod_serotonin_lr: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_NEURO_SEROTONIN_LR", 0.015)
    )
    neuromod_noradrenaline_lr: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_NEURO_NORAD_LR", 0.01)
    )
    neuromod_acetylcholine_lr: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_NEURO_ACETYL_LR", 0.01)
    )
    neuromod_urgency_factor: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_NEURO_URGENCY_FACTOR", 0.3)
    )
    neuromod_memory_factor: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_NEURO_MEMORY_FACTOR", 0.2)
    )
    neuromod_latency_scale: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_NEURO_LATENCY_SCALE", 0.05)
    )
    neuromod_accuracy_scale: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_NEURO_ACCURACY_SCALE", 0.1)
    )
    neuromod_latency_floor: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_NEURO_LATENCY_FLOOR", 0.1)
    )
    neuromod_dopamine_bias: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_NEURO_DOPAMINE_BIAS", -0.5)
    )
    neuromod_dopamine_reward_boost: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_NEURO_DOPAMINE_REWARD_BOOST", 0.1)
    )

    # Sleep system
    enable_sleep_system: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_ENABLE_SLEEP", True)
    )
    consolidation_enabled: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_CONSOLIDATION_ENABLED", True)
    )
    sleep_interval_seconds: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_SLEEP_INTERVAL_SECONDS", 3600)
    )
    sleep_k0: int = Field(default_factory=lambda: _int_env("SOMABRAIN_SLEEP_K0", 100))
    sleep_t0: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_SLEEP_T0", 10.0)
    )
    sleep_tau0: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_SLEEP_TAU0", 1.0)
    )
    sleep_eta0: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_SLEEP_ETA0", 0.1)
    )
    sleep_lambda0: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_SLEEP_LAMBDA0", 0.01)
    )
    sleep_B0: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_SLEEP_B0", 0.5)
    )
    sleep_K_min: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_SLEEP_K_MIN", 1)
    )
    sleep_t_min: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_SLEEP_T_MIN", 0.1)
    )
    sleep_alpha_K: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_SLEEP_ALPHA_K", 0.8)
    )
    sleep_alpha_t: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_SLEEP_ALPHA_T", 0.5)
    )
    sleep_alpha_tau: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_SLEEP_ALPHA_TAU", 0.5)
    )
    sleep_alpha_eta: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_SLEEP_ALPHA_ETA", 1.0)
    )
    sleep_beta_B: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_SLEEP_BETA_B", 0.5)
    )
    sleep_max_seconds: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_SLEEP_MAX_SECONDS", 3600)
    )
    max_summaries_per_cycle: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_MAX_SUMMARIES_PER_CYCLE", 3)
    )
    nrem_batch_size: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_NREM_BATCH_SIZE", 32)
    )
    rem_batch_size: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_REM_BATCH_SIZE", 32)
    )
    rem_recomb_rate: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_REM_RECOMB_RATE", 0.2)
    )

    # Predictor configuration
    predictor_provider: str = Field(
        default=_str_env("SOMABRAIN_PREDICTOR_PROVIDER", "").strip().lower() or "mahal"
    )
    predictor_dim: int = Field(default=_int_env("SOMABRAIN_PREDICTOR_DIM", 16))
    predictor_alpha: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_PREDICTOR_ALPHA", 2.0)
    )
    predictor_gamma: float = Field(
        default=_float_env("SOMABRAIN_PREDICTOR_GAMMA", -0.5)
    )
    predictor_lambda: float = Field(
        default=_float_env("SOMABRAIN_PREDICTOR_LAMBDA", 1.0)
    )
    predictor_mu: float = Field(default=_float_env("SOMABRAIN_PREDICTOR_MU", -0.25))
    predictor_timeout_ms: int = Field(default=1000)
    slow_predictor_delay_ms: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_SLOW_PREDICTOR_DELAY_MS", 1000)
    )
    relax_predictor_ready: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_RELAX_PREDICTOR_READY", False)
    )
    PREDICTOR_LATENCY_MIN: int = Field(
        default_factory=lambda: _int_env("PREDICTOR_LATENCY_MIN", 5)
    )
    PREDICTOR_LATENCY_MAX: int = Field(
        default_factory=lambda: _int_env("PREDICTOR_LATENCY_MAX", 15)
    )
    providers_path: Optional[str] = Field(default=_str_env("PROVIDERS_PATH"))

    # Heat diffusion
    heat_method: str = Field(default=_str_env("SOMA_HEAT_METHOD", "chebyshev"))
    diffusion_t: float = Field(default=_float_env("SOMABRAIN_DIFFUSION_T", 0.5))
    lanczos_m: int = Field(default=_int_env("SOMABRAIN_LANCZOS_M", 20))
    chebyshev_K: int = Field(default=_int_env("SOMABRAIN_CHEB_K", 30))

    # Calibration
    calibration_enabled: bool = Field(
        default=False, description="Enable predictor calibration service"
    )
    integrator_softmax_temperature: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_INTEGRATOR_TEMPERATURE", 1.0)
    )

    # Segmentation
    segment_grad_threshold: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_SEGMENT_GRAD_THRESH", 0.2)
    )
    segment_hmm_threshold: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_SEGMENT_HMM_THRESH", 0.6)
    )
    segment_health_port: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_SEGMENTATION_HEALTH_PORT", 9016)
    )
    segment_health_enable: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_SEGMENT_HEALTH_ENABLE", True)
    )
    segment_max_dwell_ms: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_SEGMENT_MAX_DWELL_MS", 0)
    )
    segment_min_gap_ms: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_SEGMENT_MIN_GAP_MS", 250)
    )
    segment_write_gap_threshold_ms: int = Field(
        default_factory=lambda: _int_env(
            "SOMABRAIN_SEGMENT_WRITE_GAP_THRESHOLD_MS", 30000
        )
    )
    segmentation_consumer_group: str = Field(
        default_factory=lambda: _str_env(
            "SOMABRAIN_CONSUMER_GROUP", "segmentation-service"
        )
    )

    # CPD segmentation
    cpd_min_samples: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_CPD_MIN_SAMPLES", 20)
    )
    cpd_z: float = Field(default_factory=lambda: _float_env("SOMABRAIN_CPD_Z", 4.0))
    cpd_min_gap_ms: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_CPD_MIN_GAP_MS", 1000)
    )
    cpd_min_std: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_CPD_MIN_STD", 0.02)
    )

    # Hazard segmentation
    hazard_lambda: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_HAZARD_LAMBDA", 0.02)
    )
    hazard_vol_mult: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_HAZARD_VOL_MULT", 3.0)
    )
    hazard_min_samples: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_HAZARD_MIN_SAMPLES", 20)
    )
    hazard_min_gap_ms: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_HAZARD_MIN_GAP_MS", 1000)
    )
    hazard_min_std: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_HAZARD_MIN_STD", 0.02)
    )

    # Feedback safety
    feedback_rate_limit_per_minute: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_FEEDBACK_RATE_LIMIT_PER_MIN", 120)
    )

    # Drift monitoring
    drift_store_path: str = Field(
        default_factory=lambda: _str_env(
            "SOMABRAIN_DRIFT_STORE", "./data/drift/state.json"
        )
        or "./data/drift/state.json"
    )

    # Spectral cache
    spectral_cache_dir: Optional[str] = Field(
        default=_str_env("SOMABRAIN_SPECTRAL_CACHE_DIR")
    )

    # Learner DLQ
    learner_dlq_path: str = Field(
        default=_str_env("SOMABRAIN_LEARNER_DLQ_PATH", "./data/learner_dlq.jsonl")
    )
    learner_dlq_topic: Optional[str] = Field(
        default=_str_env("SOMABRAIN_LEARNER_DLQ_TOPIC")
    )

    # LLM endpoint
    llm_endpoint: Optional[str] = Field(default=_str_env("SOMABRAIN_LLM_ENDPOINT"))
