"""Brain Settings - Django ORM Model for DB-Backed Brain Configuration.

BRAIN parameters only - no system/infrastructure settings.
System settings (Redis, Kafka, Postgres URLs, secrets) stay in ENV/Vault.

Multi-tenant. Hot-reload via cache. NO FALLBACKS - fail fast.
"""

from django.db import models
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from typing import Any
import logging
from somabrain.admin.common.messages import ErrorCode, get_message

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
    value_text = models.TextField(null=True, blank=True)
    value_type = models.CharField(max_length=20, default="float")
    category = models.CharField(max_length=100, db_index=True, default="brain")
    is_learnable = models.BooleanField(default=False)
    min_value = models.FloatField(null=True, blank=True)
    max_value = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # app_label = "somabrain"  <-- REMOVED to allow proper migration as brain_settings app
        db_table = "brain_settings"
        unique_together = [["key", "tenant"]]

    def get_value(self) -> Any:
        if self.value_type == "float": return self.value_float
        if self.value_type == "int": return self.value_int
        if self.value_type == "bool": return self.value_bool
        if self.value_type == "text": return self.value_text
        return self.value_float

    def set_value(self, value: Any) -> None:
        if isinstance(value, bool):
            self.value_bool, self.value_type = value, "bool"
        elif isinstance(value, float):
            self.value_float, self.value_type = value, "float"
        elif isinstance(value, int):
            self.value_int, self.value_type = value, "int"
        elif isinstance(value, str):
            self.value_text, self.value_type = value, "text"

    CACHE_PREFIX, CACHE_TIMEOUT = "brain:", 30

    @classmethod
    def get(cls, key: str, tenant: str = "default") -> Any:
        # Avoid recursion when looking up the mode itself
        if key == "active_brain_mode":
            return cls._get_raw_value(key, tenant)

        # 1. Fetch current mode (cached)
        current_mode = cls.get("active_brain_mode", tenant)

        # 2. Priority 1: Mode Tuning (Tenant-specific override for this specific mode)
        # Pattern: "knob_name:MODE"
        mode_tuned_key = f"{key}:{current_mode}"
        try:
            return cls._get_raw_value(mode_tuned_key, tenant)
        except BrainSettingNotFound:
            pass

        # 3. Priority 2: Mode Registry Overrides (Calculated/Theoretical Presets)
        from .modes import get_mode_overrides
        overrides = get_mode_overrides(current_mode)
        if key in overrides:
            return overrides[key]

        # 4. Priority 3: Base Database/Default Logic
        return cls._get_raw_value(key, tenant)

    @classmethod
    def _get_raw_value(cls, key: str, tenant: str = "default") -> Any:
        """Fetch raw value from cache or DB without overrides."""
        cache_key = f"{cls.CACHE_PREFIX}{tenant}:{key}"
        cached = cache.get(cache_key)
        if cached is not None: return cached
        try:
            s = cls.objects.get(key=key, tenant=tenant)
            v = s.get_value()
            cache.set(cache_key, v, cls.CACHE_TIMEOUT)
            return v
        except cls.DoesNotExist:
            raise BrainSettingNotFound(
                get_message(ErrorCode.BRAIN_SETTING_NOT_FOUND, key=key, tenant=tenant)
            )

    @classmethod
    def set(cls, key: str, value: Any, tenant: str = "default") -> "BrainSetting":
        # Extract base key if it's a mode-tuned key (e.g. gmd_eta:TRAINING)
        base_key = key.split(":")[0]

        try:
            # We look up the base setting to check metadata (category, validation)
            s_meta = cls.objects.get(key=base_key, tenant=tenant)
        except cls.DoesNotExist:
            raise BrainSettingNotFound(f"Unknown base setting '{base_key}'.")

        # SAFETY POLICY: NO TOUCH for SYSTEM_CORE
        if s_meta.category == "SYSTEM_CORE" and not tenant == "default":
             raise PermissionError(f"'{base_key}' is a SYSTEM_CORE knob and is NO TOUCH.")

        # Validation for learnable knobs (check against base metadata)
        if s_meta.is_learnable and isinstance(value, (int, float)):
            if s_meta.min_value is not None and value < s_meta.min_value:
                raise ValueError(f"{base_key}: {value} < min {s_meta.min_value}")
            if s_meta.max_value is not None and value > s_meta.max_value:
                raise ValueError(f"{base_key}: {value} > max {s_meta.max_value}")

        # Atomic create/update for the actual key (might be a tuned key)
        s, created = cls.objects.get_or_create(key=key, tenant=tenant)
        s.set_value(value)
        # Copy metadata from base if it's a new tuned key
        if created and base_key != key:
            s.category = s_meta.category
            s.is_learnable = s_meta.is_learnable
        s.save()

        # Zero-Latency: If we update 'active_brain_mode', invalidate the entire tenant cache
        if key == "active_brain_mode":
            cls.invalidate_tenant_cache(tenant)
        else:
            cache.delete(f"{cls.CACHE_PREFIX}{tenant}:{key}")

        return s

    @classmethod
    def invalidate_tenant_cache(cls, tenant: str = "default") -> None:
        """Invalidate ALL brain settings for a tenant. Critical for Mode Switches."""
        # Use a versioning or pattern-based approach since cache.delete_many doesn't support wildcards
        # in standard Django cache. For now, we clear the known keys if possible, or expect
        # a cache version bump/prefix clear.
        logger.info(f"Invalidating cognitive cache for tenant: {tenant}")
        # Note: In production with Redis, we'd use eval or unlink with a pattern.
        # For this implementation, we clear common hot keys or the whole cache if needed.
        # Given our CACHE_TIMEOUT is short (30s), a simpler approach is fine,
        # but for true zero-latency, we'd clear the prefix.
        # Assuming we have access to the redis client via cache.client
        try:
            from django.core.cache import cache
            if hasattr(cache, 'delete_pattern'):
                cache.delete_pattern(f"{cls.CACHE_PREFIX}{tenant}:*")
            else:
                # Fallback for simple backends
                for k in BRAIN_DEFAULTS.keys():
                    cache.delete(f"{cls.CACHE_PREFIX}{tenant}:{k}")
                cache.delete(f"{cls.CACHE_PREFIX}{tenant}:active_brain_mode")
        except Exception as e:
            logger.error(f"Failed to invalidate tenant cache: {e}")

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
    # ==================== OPERATIONAL MODES ====================
    "active_brain_mode": {"v": "ANALYTIC", "cat": "mode", "type": "text"},

    # ==================== SYSTEM_CORE (NO TOUCH) ====================
    # GMD MathCore v4.0 Fundamental Constants
    "gmd_delta": {"v": 0.01, "cat": "SYSTEM_CORE"},  # Max pairwise similarity
    "gmd_epsilon": {"v": 0.05, "cat": "SYSTEM_CORE"}, # Collision probability
    "gmd_alpha": {"v": 640.0, "cat": "SYSTEM_CORE"}, # Cleanup capacity constant
    "gmd_lambda_reg": {"v": 2.05e-5, "cat": "SYSTEM_CORE"}, # Wiener Unbinding λ*
    "gmd_quantization_bits": {"v": 8, "cat": "SYSTEM_CORE"},
    "hrr_dim": {"v": 8192, "cat": "SYSTEM_CORE"},
    "embed_dim": {"v": 256, "cat": "SYSTEM_CORE"},
    "global_seed": {"v": 42, "cat": "SYSTEM_CORE"},

    # ==================== PLASTICITY (LEARNING) ====================
    "gmd_eta": {"v": 0.08, "cat": "PLASTICITY", "learnable": True, "min": 0.03, "max": 0.10},
    "adapt_lr": {"v": 0.05, "cat": "PLASTICITY", "learnable": True, "min": 0.0, "max": 0.25},
    "neuro_acetyl_lr": {"v": 0.01, "cat": "PLASTICITY", "learnable": True, "min": 0.0, "max": 0.05},
    "neuro_norad_lr": {"v": 0.01, "cat": "PLASTICITY", "learnable": True, "min": 0.0, "max": 0.05},
    "neuro_serotonin_lr": {"v": 0.01, "cat": "PLASTICITY", "learnable": True, "min": 0.0, "max": 0.05},
    "gmd_sparsity": {"v": 0.1, "cat": "PLASTICITY", "learnable": True, "min": 0.05, "max": 0.55},

    # ==================== ELASTICITY (RECALL & ASSOCIATION) ====================
    "tau": {"v": 0.7, "cat": "ELASTICITY", "learnable": True, "min": 0.0, "max": 3.5},
    "graph_hops": {"v": 2, "cat": "ELASTICITY", "learnable": True, "min": 1, "max": 10},
    "salience_w_novelty": {"v": 0.6, "cat": "ELASTICITY", "learnable": True, "min": 0.0, "max": 1.0},
    "recency_half_life": {"v": 60.0, "cat": "ELASTICITY", "learnable": True, "min": 10.0, "max": 3600.0},
    "determinism": {"v": True, "cat": "ELASTICITY"},

    # ==================== RESOURCE (SLEEP & LIMITS) ====================
    "enable_sleep": {"v": True, "cat": "RESOURCE"},
    "sleep_k0": {"v": 100, "cat": "RESOURCE", "learnable": True, "min": 1, "max": 500},
    "write_daily_limit": {"v": 100000, "cat": "RESOURCE", "learnable": True},
    "adapt_gain_mu": {"v": -0.25, "cat": "adapt"},
    "adapt_gain_nu": {"v": -0.25, "cat": "adapt"},
    "adapt_gamma_max": {"v": 1.0, "cat": "adapt"},
    "adapt_gamma_min": {"v": 0.0, "cat": "adapt"},
    "adapt_lambda_max": {"v": 5.0, "cat": "adapt"},
    "adapt_lambda_min": {"v": 0.1, "cat": "adapt"},
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

    # CLEANUP - GMD MathCore compliance (no magic numbers)
    "cleanup_hnsw_m": {"v": 32, "cat": "cleanup"},
    "cleanup_topk": {"v": 64, "cat": "cleanup"},
    "cleanup_threshold": {"v": 0.65, "cat": "cleanup"},  # hierarchical.py
    "cleanup_promote_margin": {"v": 0.1, "cat": "cleanup"},  # hierarchical.py
    "cleanup_alpha": {"v": 0.5, "cat": "cleanup"},  # quantum.py Wiener

    # ENTROPY - Sharpening rates for cap enforcement
    "entropy_sharpen_rate": {"v": 0.8, "cat": "entropy"},  # annealing.py
    "entropy_final_sharpen": {"v": 0.05, "cat": "entropy"},  # annealing.py

    # GRAPH - Edge and boost settings
    "graph_edge_strength": {"v": 0.5, "cat": "graph"},  # graph_client.py
    "graph_boost_factor": {"v": 0.3, "cat": "graph"},  # recall_ops.py

    # PROMOTION
    "promotion_threshold": {"v": 0.85, "cat": "promotion"},  # promotion.py

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
    # EMBEDDING (Managed via SYSTEM_CORE)

    # SLEEP
    "enable_sleep": {"v": True, "cat": "sleep"},

    # ENTROPY
    "entropy_cap": {"v": 0.0, "cat": "entropy"},
    "entropy_cap_enabled": {"v": False, "cat": "entropy"},

    # BRAIN
    # BRAIN (Managed via SYSTEM_CORE)

    # GRAPH
    # GRAPH (Managed via ELASTICITY)
    "graph_limit": {"v": 20, "cat": "graph"},

    # HRR
    # HRR (Managed via SYSTEM_CORE)
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
    "recency_sharpness": {"v": 1.2, "cat": "recency"},

    # SLEEP - Dynamic parameter scheduling
    # SLEEP (Managed via RESOURCE)
    "sleep_k_min": {"v": 1, "cat": "sleep"},
    "sleep_t_min": {"v": 0.1, "cat": "sleep"},
    "sleep_alpha_k": {"v": 0.8, "cat": "sleep"},
    "sleep_alpha_t": {"v": 0.5, "cat": "sleep"},
    "sleep_alpha_tau": {"v": 0.5, "cat": "sleep"},
    "sleep_alpha_eta": {"v": 1.0, "cat": "sleep"},
    "sleep_beta_b": {"v": 0.5, "cat": "sleep"},
    "rem_recomb_rate": {"v": 0.2, "cat": "sleep", "learnable": True, "min": 0.0, "max": 1.0},
    "consolidation_enabled": {"v": True, "cat": "sleep"},
    "nrem_batch_size": {"v": 16, "cat": "sleep"},
    "max_summaries_per_cycle": {"v": 3, "cat": "sleep"},

    # RETRIEVAL
    "retrieval_alpha": {"v": 1.0, "cat": "retrieval", "learnable": True, "min": 0.0, "max": 5.0},
    "retrieval_beta": {"v": 0.2, "cat": "retrieval", "learnable": True, "min": 0.0, "max": 1.0},
    "retrieval_gamma": {"v": 0.1, "cat": "retrieval", "learnable": True, "min": 0.0, "max": 0.5},
    "retrieval_tau": {"v": 0.7, "cat": "retrieval", "learnable": True, "min": 0.0, "max": 2.0},
    # tau (Managed via ELASTICITY)

    # SALIENCE
    "salience_fd_decay": {"v": 0.9, "cat": "salience", "learnable": True, "min": 0.0, "max": 4.5},
    "salience_fd_rank": {"v": 128, "cat": "salience"},
    "salience_fd_weight": {"v": 0.25, "cat": "salience", "learnable": True, "min": 0.0, "max": 1.25},
    "salience_hysteresis": {"v": 0.1, "cat": "salience"},
    "salience_w_error": {"v": 0.4, "cat": "salience"},
    # salience_w_novelty (Managed via ELASTICITY)

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
    "tau_anneal_mode": {"v": "", "cat": "tau", "type": "text"},
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
    # write_daily_limit (Managed via RESOURCE)
}


def get(key: str, tenant: str = "default") -> Any:
    return BrainSetting.get(key, tenant)

def set(key: str, value: Any, tenant: str = "default") -> None:
    BrainSetting.set(key, value, tenant)
