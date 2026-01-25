"""Brain Settings - Django ORM Model for DB-Backed Brain Configuration.

BRAIN parameters only - no system/infrastructure settings.
System settings (Redis, Kafka, Postgres URLs, secrets) stay in ENV/Vault.

Multi-tenant. Hot-reload via cache. NO FALLBACKS - fail fast.
"""

from django.db import models
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from typing import Any, Dict, Tuple
import logging

logger = logging.getLogger(__name__)


class BrainSettingNotFound(ImproperlyConfigured):
    """Brain setting not in DB. Run initialize_defaults() first."""
    pass


class BrainSetting(models.Model):
    """Brain setting stored in database. Multi-tenant, hot-reload."""

    key = models.CharField(max_length=255, db_index=True)
    tenant = models.CharField(max_length=100, default="default", db_index=True)
    value_float = models.FloatField(null=True, blank=True)
    value_int = models.IntegerField(null=True, blank=True)
    value_bool = models.BooleanField(null=True, blank=True)
    value_type = models.CharField(max_length=20, default="float")
    category = models.CharField(max_length=100, db_index=True, default="brain")
    is_learnable = models.BooleanField(default=False)
    min_value = models.FloatField(null=True, blank=True)
    max_value = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "somabrain"
        db_table = "brain_settings"
        unique_together = [["key", "tenant"]]

    def get_value(self) -> Any:
        if self.value_type == "float": return self.value_float
        if self.value_type == "int": return self.value_int
        if self.value_type == "bool": return self.value_bool
        return self.value_float

    def set_value(self, value: Any) -> None:
        if isinstance(value, bool):
            self.value_bool, self.value_type = value, "bool"
        elif isinstance(value, float):
            self.value_float, self.value_type = value, "float"
        elif isinstance(value, int):
            self.value_int, self.value_type = value, "int"

    CACHE_PREFIX, CACHE_TIMEOUT = "brain:", 30

    @classmethod
    def get(cls, key: str, tenant: str = "default") -> Any:
        cache_key = f"{cls.CACHE_PREFIX}{tenant}:{key}"
        cached = cache.get(cache_key)
        if cached is not None: return cached
        try:
            s = cls.objects.get(key=key, tenant=tenant)
            v = s.get_value()
            cache.set(cache_key, v, cls.CACHE_TIMEOUT)
            return v
        except cls.DoesNotExist:
            raise BrainSettingNotFound(f"'{key}' not found. Run initialize_defaults().")

    @classmethod
    def set(cls, key: str, value: Any, tenant: str = "default") -> "BrainSetting":
        try:
            s = cls.objects.get(key=key, tenant=tenant)
        except cls.DoesNotExist:
            raise BrainSettingNotFound(f"Unknown setting '{key}'.")
        if s.is_learnable and isinstance(value, (int, float)):
            if s.min_value is not None and value < s.min_value:
                raise ValueError(f"{key}: {value} < min {s.min_value}")
            if s.max_value is not None and value > s.max_value:
                raise ValueError(f"{key}: {value} > max {s.max_value}")
        s.set_value(value)
        s.save()
        cache.delete(f"{cls.CACHE_PREFIX}{tenant}:{key}")
        return s

    @classmethod
    def initialize_defaults(cls, tenant: str = "default") -> int:
        created = 0
        for key, cfg in BRAIN_DEFAULTS.items():
            obj, was_created = cls.objects.get_or_create(
                key=key, tenant=tenant,
                defaults={"category": cfg.get("cat", "brain"), "is_learnable": cfg.get("learnable", False),
                          "min_value": cfg.get("min"), "max_value": cfg.get("max")})
            if was_created:
                obj.set_value(cfg["v"])
                obj.save()
                created += 1
        logger.info(f"Initialized {created} brain settings for {tenant}")
        return created


# =========== BRAIN DEFAULTS (145 settings) ===========

BRAIN_DEFAULTS = {
    # ==================== GMD MathCore v4.0 ====================
    # Theorem 1: Optimal Encoding p* = (1+√δ)/2
    "gmd_sparsity": {"v": 0.1, "cat": "gmd", "learnable": True, "min": 0.05, "max": 0.55},
    "gmd_delta": {"v": 0.01, "cat": "gmd"},  # Max pairwise similarity
    "gmd_epsilon": {"v": 0.05, "cat": "gmd"},  # Collision probability

    # Theorem 2: Bayesian Memory - SNR = (2η-η²)/(N-1) · D/p(1-p)
    "gmd_eta": {"v": 0.08, "cat": "gmd", "learnable": True, "min": 0.03, "max": 0.10},
    "gmd_alpha": {"v": 640.0, "cat": "gmd"},  # Cleanup capacity constant
    "gmd_target_gamma": {"v": 0.8, "cat": "gmd"},  # Target recall quality

    # Theorem 3: Wiener Unbinding λ* = (2/255)²/3 ≈ 2.05e-5
    "gmd_lambda_reg": {"v": 2.05e-5, "cat": "gmd"},
    "gmd_quantization_bits": {"v": 8, "cat": "gmd"},

    # Theorem 5: Robust Region
    "gmd_robust_eta_min": {"v": 0.03, "cat": "gmd"},
    "gmd_robust_eta_max": {"v": 0.10, "cat": "gmd"},
    "gmd_robust_p_min": {"v": 0.05, "cat": "gmd"},
    "gmd_robust_p_max": {"v": 0.20, "cat": "gmd"},
    "gmd_robust_lambda_min": {"v": 1e-6, "cat": "gmd"},
    "gmd_robust_lambda_max": {"v": 1e-4, "cat": "gmd"},

    # ADAPT
    "adapt_alpha_max": {"v": 5.0, "cat": "adapt"},

    "adapt_alpha_min": {"v": 0.1, "cat": "adapt"},
    "adapt_gain_alpha": {"v": 1.0, "cat": "adapt", "learnable": True, "min": 0.0, "max": 5.0},
    "adapt_gain_gamma": {"v": -0.5, "cat": "adapt", "learnable": True, "min": 0.0, "max": 1.0},
    "adapt_gain_lambda": {"v": 1.0, "cat": "adapt"},
    "adapt_gain_mu": {"v": -0.25, "cat": "adapt"},
    "adapt_gain_nu": {"v": -0.25, "cat": "adapt"},
    "adapt_gamma_max": {"v": 1.0, "cat": "adapt"},
    "adapt_gamma_min": {"v": 0.0, "cat": "adapt"},
    "adapt_lambda_max": {"v": 5.0, "cat": "adapt"},
    "adapt_lambda_min": {"v": 0.1, "cat": "adapt"},
    "adapt_lr": {"v": 0.05, "cat": "adapt", "learnable": True, "min": 0.0, "max": 0.25},
    "adapt_max_history": {"v": 1000, "cat": "adapt"},
    "adapt_mu_max": {"v": 5.0, "cat": "adapt"},
    "adapt_mu_min": {"v": 0.01, "cat": "adapt"},
    "adapt_nu_max": {"v": 5.0, "cat": "adapt"},
    "adapt_nu_min": {"v": 0.01, "cat": "adapt"},
    "adaptation_gain_mu": {"v": -0.25, "cat": "adapt"},
    "adaptation_gain_nu": {"v": -0.25, "cat": "adapt"},
    "adaptation_mu_max": {"v": 5.0, "cat": "adapt"},
    "adaptation_mu_min": {"v": 0.01, "cat": "adapt"},
    "adaptation_nu_max": {"v": 5.0, "cat": "adapt"},
    "adaptation_nu_min": {"v": 0.01, "cat": "adapt"},

    # HRR
    "bhdc_sparsity": {"v": 0.1, "cat": "hrr"},

    # CLEANUP
    "cleanup_hnsw_m": {"v": 32, "cat": "cleanup"},
    "cleanup_topk": {"v": 64, "cat": "cleanup"},

    # WM
    "default_wm_slots": {"v": 12, "cat": "wm"},

    # RECENCY
    "density_floor": {"v": 0.6, "cat": "recency", "learnable": True, "min": 0.0, "max": 3.0},
    "density_target": {"v": 0.2, "cat": "recency"},
    "density_weight": {"v": 0.35, "cat": "recency", "learnable": True, "min": 0.0, "max": 1.75},

    # BRAIN
    "determinism": {"v": True, "cat": "brain"},
    "dup_ratio_threshold": {"v": 0.5, "cat": "brain", "learnable": True, "min": 0.0, "max": 2.5},

    # EMBEDDING
    "embed_dim": {"v": 256, "cat": "embedding"},

    # SLEEP
    "enable_sleep": {"v": True, "cat": "sleep"},

    # ENTROPY
    "entropy_cap": {"v": 0.0, "cat": "entropy"},
    "entropy_cap_enabled": {"v": False, "cat": "entropy"},

    # BRAIN
    "global_seed": {"v": 42, "cat": "brain"},

    # GRAPH
    "graph_hops": {"v": 2, "cat": "graph"},
    "graph_limit": {"v": 20, "cat": "graph"},

    # HRR
    "hrr_dim": {"v": 8192, "cat": "hrr"},
    "hrr_renorm": {"v": True, "cat": "hrr"},

    # CONTEXT
    "max_superpose": {"v": 32, "cat": "context"},

    # BRAIN
    "memory_fast_ack": {"v": False, "cat": "brain"},
    "memory_quality_exp": {"v": 1.0, "cat": "brain"},

    # CIRCUIT
    "micro_circuits": {"v": 1, "cat": "circuit"},
    "micro_max_tenants": {"v": 1000, "cat": "circuit"},

    # WM
    "mtwm_max_tenants": {"v": 1000, "cat": "wm"},

    # NEURO - Dynamics Constants (dm/dt = k_d*x - k_r*m + bias + u_scale*u)
    # k_d: drive coefficients [dopamine, serotonin, norad, acetyl]
    "neuro_k_d_dopamine": {"v": 0.8, "cat": "neuro", "learnable": True, "min": 0.0, "max": 2.0},
    "neuro_k_d_serotonin": {"v": 0.3, "cat": "neuro", "learnable": True, "min": 0.0, "max": 1.0},
    "neuro_k_d_norad": {"v": 0.1, "cat": "neuro", "learnable": True, "min": 0.0, "max": 0.5},
    "neuro_k_d_acetyl": {"v": 0.2, "cat": "neuro", "learnable": True, "min": 0.0, "max": 0.5},
    # k_r: recovery coefficients
    "neuro_k_r_dopamine": {"v": 0.1, "cat": "neuro", "learnable": True, "min": 0.0, "max": 0.5},
    "neuro_k_r_serotonin": {"v": 0.2, "cat": "neuro", "learnable": True, "min": 0.0, "max": 0.5},
    "neuro_k_r_norad": {"v": 0.3, "cat": "neuro", "learnable": True, "min": 0.0, "max": 1.0},
    "neuro_k_r_acetyl": {"v": 0.4, "cat": "neuro", "learnable": True, "min": 0.0, "max": 1.0},
    # u_scale: control input scaling
    "neuro_u_scale": {"v": 0.1, "cat": "neuro", "learnable": True, "min": 0.0, "max": 0.5},
    # Existing neuro settings
    "neuro_acetyl_base": {"v": 0.0, "cat": "neuro", "learnable": True, "min": 0.0, "max": 1.0},
    "neuro_acetyl_lr": {"v": 0.01, "cat": "neuro", "learnable": True, "min": 0.0, "max": 0.05},
    "neuro_acetyl_max": {"v": 0.1, "cat": "neuro"},
    "neuro_acetyl_min": {"v": 0.0, "cat": "neuro"},

    "neuro_latency_floor": {"v": 0.1, "cat": "neuro", "learnable": True, "min": 0.0, "max": 0.5},
    "neuro_latency_scale": {"v": 0.01, "cat": "neuro", "learnable": True, "min": 0.0, "max": 0.05},
    "neuro_memory_factor": {"v": 0.02, "cat": "neuro", "learnable": True, "min": 0.0, "max": 0.1},
    "neuro_norad_base": {"v": 0.0, "cat": "neuro", "learnable": True, "min": 0.0, "max": 1.0},
    "neuro_norad_lr": {"v": 0.01, "cat": "neuro", "learnable": True, "min": 0.0, "max": 0.05},
    "neuro_norad_max": {"v": 0.1, "cat": "neuro"},
    "neuro_norad_min": {"v": 0.0, "cat": "neuro"},
    "neuro_serotonin_lr": {"v": 0.01, "cat": "neuro", "learnable": True, "min": 0.0, "max": 0.05},
    "neuro_serotonin_max": {"v": 1.0, "cat": "neuro"},
    "neuro_serotonin_min": {"v": 0.0, "cat": "neuro"},

    # PLANNER
    "plan_max_steps": {"v": 5, "cat": "planner"},
    "planner_rwr_max_items": {"v": 5, "cat": "planner"},
    "planner_rwr_restart": {"v": 0.15, "cat": "planner"},
    "planner_rwr_steps": {"v": 20, "cat": "planner"},

    # PREDICTOR
    "predictor_alpha": {"v": 2.0, "cat": "predictor", "learnable": True, "min": 0.0, "max": 10.0},
    "predictor_dim": {"v": 16, "cat": "predictor"},
    "predictor_gamma": {"v": -0.5, "cat": "predictor", "learnable": True, "min": 0.0, "max": 1.0},

    # HRR
    "quantum_dim": {"v": 2048, "cat": "hrr"},
    "quantum_sparsity": {"v": 0.1, "cat": "hrr"},

    # QUOTA
    "quota_action": {"v": 500, "cat": "quota"},
    "quota_tenant": {"v": 10000, "cat": "quota"},
    "quota_tool": {"v": 1000, "cat": "quota"},

    # RATE
    "rate_burst": {"v": 2000, "cat": "rate"},
    "rate_rps": {"v": 1000, "cat": "rate"},

    # RECALL
    "recall_full_power": {"v": True, "cat": "recall"},

    # RECENCY
    "recency_floor": {"v": 0.05, "cat": "recency", "learnable": True, "min": 0.0, "max": 0.25},
    "recency_half_life": {"v": 60.0, "cat": "recency"},
    "recency_sharpness": {"v": 1.2, "cat": "recency"},

    # SLEEP
    "rem_recomb_rate": {"v": 0.2, "cat": "sleep", "learnable": True, "min": 0.0, "max": 1.0},

    # RETRIEVAL
    "retrieval_alpha": {"v": 1.0, "cat": "retrieval", "learnable": True, "min": 0.0, "max": 5.0},
    "retrieval_beta": {"v": 0.2, "cat": "retrieval", "learnable": True, "min": 0.0, "max": 1.0},
    "retrieval_gamma": {"v": 0.1, "cat": "retrieval", "learnable": True, "min": 0.0, "max": 0.5},
    "retrieval_tau": {"v": 0.7, "cat": "retrieval", "learnable": True, "min": 0.0, "max": 3.5},

    # SALIENCE
    "salience_fd_decay": {"v": 0.9, "cat": "salience", "learnable": True, "min": 0.0, "max": 4.5},
    "salience_fd_rank": {"v": 128, "cat": "salience"},
    "salience_fd_weight": {"v": 0.25, "cat": "salience", "learnable": True, "min": 0.0, "max": 1.25},
    "salience_hysteresis": {"v": 0.1, "cat": "salience"},
    "salience_w_error": {"v": 0.4, "cat": "salience"},
    "salience_w_novelty": {"v": 0.6, "cat": "salience"},

    # SCORER
    "scorer_recency_tau": {"v": 32.0, "cat": "scorer", "learnable": True, "min": 0.0, "max": 160.0},
    "scorer_w_cosine": {"v": 0.6, "cat": "scorer"},
    "scorer_w_fd": {"v": 0.25, "cat": "scorer"},
    "scorer_w_recency": {"v": 0.15, "cat": "scorer"},
    "scorer_weight_max": {"v": 1.0, "cat": "scorer"},
    "scorer_weight_min": {"v": 0.0, "cat": "scorer"},

    # SDR
    "sdr_bits": {"v": 2048, "cat": "sdr"},
    "sdr_density": {"v": 0.03, "cat": "sdr"},
    "sdr_dim": {"v": 16384, "cat": "sdr"},
    "sdr_sparsity": {"v": 0.01, "cat": "sdr"},

    # SEGMENT
    "segment_grad_thresh": {"v": 0.2, "cat": "segment"},
    "segment_hmm_thresh": {"v": 0.6, "cat": "segment"},

    # TAU
    "tau_anneal_rate": {"v": 0.0, "cat": "tau", "learnable": True, "min": 0.0, "max": 1.0},
    "tau_decay_enabled": {"v": False, "cat": "tau"},
    "tau_decay_rate": {"v": 0.0, "cat": "tau", "learnable": True, "min": 0.0, "max": 1.0},
    "tau_inc_down": {"v": 0.05, "cat": "tau", "learnable": True, "min": 0.0, "max": 0.25},
    "tau_inc_up": {"v": 0.1, "cat": "tau", "learnable": True, "min": 0.0, "max": 0.5},
    "tau_max": {"v": 1.2, "cat": "tau"},
    "tau_min": {"v": 0.4, "cat": "tau"},

    # BRAIN
    "use_drift_monitor": {"v": False, "cat": "brain"},
    "use_exec_controller": {"v": False, "cat": "brain"},
    "use_focus_state": {"v": True, "cat": "brain"},

    # GRAPH
    "use_graph_augment": {"v": False, "cat": "graph"},

    # HRR
    "use_hrr": {"v": False, "cat": "hrr"},
    "use_hrr_first": {"v": False, "cat": "hrr"},

    # BRAIN
    "use_meta_brain": {"v": False, "cat": "brain"},

    # CIRCUIT
    "use_microcircuits": {"v": False, "cat": "circuit"},

    # PLANNER
    "use_planner": {"v": False, "cat": "planner"},

    # SDR
    "use_sdr_prefilter": {"v": False, "cat": "sdr"},

    # SALIENCE
    "use_soft_salience": {"v": False, "cat": "salience"},

    # UTILITY
    "utility_lambda": {"v": 1.0, "cat": "utility"},
    "utility_lambda_max": {"v": 5.0, "cat": "utility"},
    "utility_lambda_min": {"v": 0.0, "cat": "utility"},
    "utility_mu": {"v": 0.1, "cat": "utility"},
    "utility_mu_max": {"v": 5.0, "cat": "utility"},
    "utility_mu_min": {"v": 0.0, "cat": "utility"},
    "utility_nu": {"v": 0.05, "cat": "utility"},
    "utility_nu_max": {"v": 5.0, "cat": "utility"},
    "utility_nu_min": {"v": 0.0, "cat": "utility"},

    # WM
    "wm_alpha": {"v": 0.6, "cat": "wm", "learnable": True, "min": 0.0, "max": 3.0},
    "wm_beta": {"v": 0.3, "cat": "wm", "learnable": True, "min": 0.0, "max": 1.5},
    "wm_gamma": {"v": 0.1, "cat": "wm", "learnable": True, "min": 0.0, "max": 0.5},
    "wm_recency_max_steps": {"v": 1000, "cat": "wm"},
    "wm_size": {"v": 64, "cat": "wm"},
    "wm_vote_entropy_eps": {"v": 1e-09, "cat": "wm"},

    # BRAIN
    "write_daily_limit": {"v": 100000, "cat": "brain"},
}


def get(key: str, tenant: str = "default") -> Any:
    return BrainSetting.get(key, tenant)

def set(key: str, value: Any, tenant: str = "default") -> None:
    BrainSetting.set(key, value, tenant)
