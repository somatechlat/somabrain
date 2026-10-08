"""Brain Settings - Django ORM Model for DB-Backed Brain Configuration.

BRAIN parameters only - no system/infrastructure settings.
System settings (Redis, Kafka, Postgres URLs, secrets) stay in ENV/Vault.

Multi-tenant. Hot-reload via cache. NO FALLBACKS - fail fast.

T-5: there is no silent default tenant. Every read and write names its
tenant; a missing tenant raises. Tenants with no rows of their own inherit
from the operator-chosen base profile (``SOMABRAIN_DEFAULT_TENANT``) until
they store an explicit override — that is inheritance of a real named
profile, not a fallback identity.
"""

import logging
from typing import Any

from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.db import models

from somabrain.admin.common.messages import ErrorCode, get_message

logger = logging.getLogger(__name__)


class BrainSettingNotFound(ImproperlyConfigured):
    """Brain setting not in DB. Seed the profile first.

    Operator action: ``python manage.py init_brain_settings --tenant <tenant>``.
    """


def _base_profile() -> str:
    """Return the operator-chosen base profile for brain-setting inheritance.

    This is a **real tenant**, not a silent fallback: the name comes from the
    ``SOMABRAIN_DEFAULT_TENANT`` setting (deployment topology) and a missing
    or empty value raises (``require_setting`` / ``require_tenant``, Rule 91).
    It is the inheritance parent every other tenant reads through, and the
    only tenant allowed to write ``SYSTEM_CORE`` knobs.
    """
    from somabrain.settings.resolve import require_setting, require_tenant

    return require_tenant(require_setting("SOMABRAIN_DEFAULT_TENANT"))



class BrainSetting(models.Model):
    """Brain setting stored in database. Multi-tenant, hot-reload."""

    key = models.CharField(max_length=255, db_index=True)
    # Required identity (T-5). No schema default: an uninitialised tenant and
    # an initialised one must never look identical. Call sites pass the real
    # tenant through ``require_tenant``.
    tenant = models.CharField(max_length=100, db_index=True)
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
        """Return the active typed value for the setting row."""
        if self.value_type == "float":
            return self.value_float
        if self.value_type == "int":
            return self.value_int
        if self.value_type == "bool":
            return self.value_bool
        if self.value_type == "text":
            return self.value_text
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
    def get(cls, key: str, tenant: str) -> Any:
        """Return a brain knob for *tenant*. *tenant* is required (T-5)."""
        from somabrain.settings.resolve import require_tenant

        tenant = require_tenant(tenant)
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
    def _get_raw_value(cls, key: str, tenant: str) -> Any:
        """Fetch raw value from cache or DB without overrides.

        *tenant* is required. A tenant with no rows of its own inherits from
        the operator-chosen base profile (``_base_profile``) — a real named
        tenant, not a silent default identity.
        """
        from somabrain.settings.resolve import require_tenant

        tenant = require_tenant(tenant)
        cache_key = f"{cls.CACHE_PREFIX}{tenant}:{key}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached
        try:
            s = cls.objects.get(key=key, tenant=tenant)
            v = s.get_value()
            cache.set(cache_key, v, cls.CACHE_TIMEOUT)
            return v
        except cls.DoesNotExist:
            base = _base_profile()
            if tenant != base:
                # Tenants inherit the base profile until they store an explicit
                # override. This keeps per-tenant runtime components usable
                # without pre-seeding every tenant row up front.
                base_value = cls._get_raw_value(key, base)
                cache.set(cache_key, base_value, cls.CACHE_TIMEOUT)
                return base_value
            raise BrainSettingNotFound(
                get_message(ErrorCode.BRAIN_SETTING_NOT_FOUND, key=key, tenant=tenant)
                + f" Operator action: `python manage.py init_brain_settings "
                f"--tenant {tenant}`."
            )

    @classmethod
    def set(cls, key: str, value: Any, tenant: str) -> "BrainSetting":
        """Write a brain knob for *tenant*. *tenant* is required (T-5)."""
        from somabrain.settings.resolve import require_tenant

        tenant = require_tenant(tenant)
        # Extract base key if it's a mode-tuned key (e.g. gmd_eta:TRAINING)
        base_key = key.split(":")[0]

        try:
            # We look up the base setting to check metadata (category, validation)
            s_meta = cls.objects.get(key=base_key, tenant=tenant)
        except cls.DoesNotExist:
            raise BrainSettingNotFound(
                f"Unknown base setting '{base_key}' for tenant '{tenant}'. "
                f"Operator action: `python manage.py init_brain_settings "
                f"--tenant {tenant}`."
            )

        # SAFETY POLICY: NO TOUCH for SYSTEM_CORE except the base profile
        if s_meta.category == "SYSTEM_CORE" and tenant != _base_profile():
            raise PermissionError(
                f"'{base_key}' is a SYSTEM_CORE knob and is NO TOUCH."
            )

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
    def invalidate_tenant_cache(cls, tenant: str) -> None:
        """Invalidate ALL brain settings for a tenant. Critical for Mode Switches.

        *tenant* is required (T-5).
        """
        from somabrain.settings.resolve import require_tenant

        tenant = require_tenant(tenant)
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
            if hasattr(cache, "delete_pattern"):
                cache.delete_pattern(f"{cls.CACHE_PREFIX}{tenant}:*")
            else:
                # Fallback for simple backends
                for k in BRAIN_DEFAULTS:
                    cache.delete(f"{cls.CACHE_PREFIX}{tenant}:{k}")
                cache.delete(f"{cls.CACHE_PREFIX}{tenant}:active_brain_mode")
        except Exception as e:
            logger.error(f"Failed to invalidate tenant cache: {e}")

    @classmethod
    def initialize_defaults(cls, tenant: str) -> int:
        """Seed the declared schema for *tenant*. *tenant* is required (T-5)."""
        from somabrain.settings.resolve import require_tenant

        tenant = require_tenant(tenant)
        created = 0
        for key, cfg in BRAIN_DEFAULTS.items():
            obj, was_created = cls.objects.get_or_create(
                key=key,
                tenant=tenant,
                defaults={
                    "category": cfg.get("cat", "brain"),
                    "is_learnable": cfg.get("learnable", False),
                    "min_value": cfg.get("min"),
                    "max_value": cfg.get("max"),
                },
            )
            if was_created:
                obj.set_value(cfg["v"])
                obj.save()
                created += 1
        logger.info(f"Initialized {created} brain settings for {tenant}")
        return created

    @classmethod
    def ensure_seeded(cls, tenant: str) -> bool:
        """Materialise the declared schema for a tenant that has no profile.

        ``BRAIN_DEFAULTS`` is the one declaration of every knob (R-VAL-01).
        This bootstrap turns that declaration into real rows. It is **not** a
        read-time default: ``get`` still refuses on a miss, so an unseeded
        tenant never looks seeded.

        The operator-chosen base profile (``_base_profile``) is seeded first
        because it is the inheritance base every other tenant reads through
        (``_get_raw_value``). A tenant with no rows of its own is then seeded
        from the same declaration so it can hold explicit overrides later.

        *tenant* is required (T-5). Returns True when this call created the
        profile.
        """
        from somabrain.settings.resolve import require_tenant

        tenant = require_tenant(tenant)
        created = False
        base = _base_profile()
        if not cls.objects.filter(tenant=base).exists():
            cls.initialize_defaults(base)
            created = True
        if tenant != base and not cls.objects.filter(tenant=tenant).exists():
            cls.initialize_defaults(tenant)
            created = True
        return created


# =========== BRAIN DEFAULTS (145 settings) ===========


def _default_wiener_lambda() -> float:
    """λ* = Δ² / (12 p (1−p)) at the production sparsity (GMD Theorem 3).

    Computed from the formula — never a hardcoded constant. Same source as
    `somabrain.math.bhdc_encoder.compute_wiener_lambda`.
    """
    from somabrain.math.bhdc_encoder import production_wiener_lambda

    return production_wiener_lambda()


BRAIN_DEFAULTS = {
    # ==================== OPERATIONAL MODES ====================
    "active_brain_mode": {"v": "ANALYTIC", "cat": "mode", "type": "text"},
    # ==================== TOPOLOGY (DB-managed URLs — not env) ====================
    # Operator law: URLs and hosts are administerable settings, never ENV.
    "memory_http_endpoint": {"v": "", "cat": "TOPOLOGY", "type": "text"},
    "kafka_bootstrap_servers": {"v": "", "cat": "TOPOLOGY", "type": "text"},
    "opa_url": {"v": "", "cat": "TOPOLOGY", "type": "text"},
    "redis_host": {"v": "", "cat": "TOPOLOGY", "type": "text"},
    "redis_port": {"v": 6379, "cat": "TOPOLOGY"},
    "api_url": {"v": "", "cat": "TOPOLOGY", "type": "text"},
    "milvus_host": {"v": "", "cat": "TOPOLOGY", "type": "text"},
    "milvus_port": {"v": 19530, "cat": "TOPOLOGY"},
    "schema_registry_url": {"v": "", "cat": "TOPOLOGY", "type": "text"},
    "auth_url": {"v": "", "cat": "TOPOLOGY", "type": "text"},
    # ==================== SYSTEM_CORE (NO TOUCH) ====================
    # Only keys with a live reader. Dead GMD knobs (gmd_delta/epsilon/alpha/
    # quantization_bits) deleted — declared but never consumed (audit 2026-10-08).
    # Wiener Unbinding λ* = Δ² / (12 p (1−p)) — live via admin/core/quantum.py
    "gmd_lambda_reg": {"v": _default_wiener_lambda(), "cat": "SYSTEM_CORE"},
    "hrr_dim": {"v": 8192, "cat": "SYSTEM_CORE"},
    "embed_dim": {"v": 768, "cat": "SYSTEM_CORE"},
    # ==================== PLASTICITY (LEARNING) ====================
    "gmd_eta": {
        "v": 0.08,
        "cat": "PLASTICITY",
        "learnable": True,
        "min": 0.03,
        "max": 0.10,
    },
    "adapt_lr": {
        "v": 0.05,
        "cat": "PLASTICITY",
        "learnable": True,
        "min": 0.0,
        "max": 0.25,
    },
    "gmd_sparsity": {
        "v": 0.1,
        "cat": "PLASTICITY",
        "learnable": True,
        "min": 0.05,
        "max": 0.55,
    },
    # ==================== ELASTICITY (RECALL & ASSOCIATION) ====================
    "tau": {"v": 0.7, "cat": "ELASTICITY", "learnable": True, "min": 0.0, "max": 3.5},
    "recency_half_life": {
        "v": 60.0,
        "cat": "ELASTICITY",
        "learnable": True,
        "min": 10.0,
        "max": 3600.0,
    },
    # ==================== RESOURCE (SLEEP & LIMITS) ====================
    "enable_sleep": {"v": True, "cat": "RESOURCE"},
    "sleep_k0": {"v": 100, "cat": "RESOURCE", "learnable": True, "min": 1, "max": 500},
    "sleep_t0": {
        "v": 1.0,
        "cat": "RESOURCE",
        "learnable": True,
        "min": 0.1,
        "max": 10.0,
    },
    "sleep_tau0": {
        "v": 0.1,
        "cat": "RESOURCE",
        "learnable": True,
        "min": 0.01,
        "max": 1.0,
    },
    "sleep_eta0": {
        "v": 0.01,
        "cat": "RESOURCE",
        "learnable": True,
        "min": 0.001,
        "max": 1.0,
    },
    "sleep_lambda0": {
        "v": 0.5,
        "cat": "RESOURCE",
        "learnable": True,
        "min": 0.01,
        "max": 1.0,
    },
    "sleep_b0": {
        "v": 1.0,
        "cat": "RESOURCE",
        "learnable": True,
        "min": 0.1,
        "max": 10.0,
    },
    "sleep_k_min": {
        "v": 5,
        "cat": "RESOURCE",
        "learnable": False,
        "min": 1,
        "max": 100,
    },
    "sleep_t_min": {
        "v": 0.5,
        "cat": "RESOURCE",
        "learnable": False,
        "min": 0.1,
        "max": 5.0,
    },
    "sleep_alpha_k": {
        "v": 0.1,
        "cat": "RESOURCE",
        "learnable": True,
        "min": 0.0,
        "max": 1.0,
    },
    "sleep_alpha_t": {
        "v": 0.05,
        "cat": "RESOURCE",
        "learnable": True,
        "min": 0.0,
        "max": 1.0,
    },
    "sleep_alpha_tau": {
        "v": 0.05,
        "cat": "RESOURCE",
        "learnable": True,
        "min": 0.0,
        "max": 1.0,
    },
    "sleep_alpha_eta": {
        "v": 0.01,
        "cat": "RESOURCE",
        "learnable": True,
        "min": 0.0,
        "max": 1.0,
    },
    "sleep_beta_b": {
        "v": 0.1,
        "cat": "RESOURCE",
        "learnable": True,
        "min": 0.0,
        "max": 1.0,
    },
    # DEF-13 FIXED: one adaptation namespace (adaptation_* matches
    # SOMABRAIN_ADAPTATION_* env keys).  Duplicate adapt_* entries deleted.
    "adapt_max_history": {"v": 1000, "cat": "adapt"},
    "adaptation_gain_mu": {"v": -0.25, "cat": "adapt"},
    "adaptation_gain_nu": {"v": -0.25, "cat": "adapt"},
    # HRR
    # CLEANUP - GMD MathCore compliance (no magic numbers)
    "cleanup_topk": {"v": 64, "cat": "cleanup"},
    "cleanup_threshold": {"v": 0.65, "cat": "cleanup"},  # hierarchical.py
    "cleanup_promote_margin": {"v": 0.1, "cat": "cleanup"},  # hierarchical.py
    "cleanup_alpha": {"v": 0.5, "cat": "cleanup"},  # quantum.py Wiener
    # ENTROPY - Sharpening rates for cap enforcement
    "entropy_sharpen_rate": {"v": 0.8, "cat": "entropy"},  # annealing.py
    "entropy_final_sharpen": {"v": 0.05, "cat": "entropy"},  # annealing.py
    # GRAPH - Edge and boost settings  # graph_client.py
    "graph_boost_factor": {"v": 0.3, "cat": "graph"},  # recall_ops.py
    # PROMOTION
    "promotion_threshold": {"v": 0.85, "cat": "promotion"},  # promotion.py
    # WM
    # RECENCY
    "density_floor": {
        "v": 0.6,
        "cat": "recency",
        "learnable": True,
        "min": 0.0,
        "max": 3.0,
    },
    "density_target": {"v": 0.2, "cat": "recency"},
    "density_weight": {
        "v": 0.35,
        "cat": "recency",
        "learnable": True,
        "min": 0.0,
        "max": 1.75,
    },
    # EMBEDDING
    # EMBEDDING (Managed via SYSTEM_CORE)
    # ENTROPY
    "entropy_cap": {"v": 0.0, "cat": "entropy"},
    # BRAIN
    # BRAIN (Managed via SYSTEM_CORE)
    # GRAPH
    # GRAPH (Managed via ELASTICITY)
    # HRR
    # HRR (Managed via SYSTEM_CORE)
    # CONTEXT
    # BRAIN
    # CIRCUIT
    # WM
    # PLANNER
    "plan_max_steps": {"v": 5, "cat": "planner"},
    "planner_rwr_max_items": {"v": 5, "cat": "planner"},
    "planner_rwr_restart": {"v": 0.15, "cat": "planner"},
    "planner_rwr_steps": {"v": 20, "cat": "planner"},
    # PREDICTOR
    # DEF-09 FIXED (W3): default is contracts.ADAPT_GAINS["gamma"] = -0.5.
    # Bounds include that value so set() cannot reject the seeded default.
    # HRR
    "quantum_dim": {"v": 2048, "cat": "hrr"},
    # QUOTA
    # RATE
    # RECALL
    # RECENCY
    "recency_floor": {
        "v": 0.05,
        "cat": "recency",
        "learnable": True,
        "min": 0.0,
        "max": 0.25,
    },
    "recency_sharpness": {"v": 1.2, "cat": "recency"},
    # SLEEP (Managed via RESOURCE block above — DEF-12 fixed: duplicate
    # sleep_k_min/t_min/alpha_* entries removed; the RESOURCE block at lines
    # 336-383 is the single definition.)
    "rem_recomb_rate": {
        "v": 0.2,
        "cat": "sleep",
        "learnable": True,
        "min": 0.0,
        "max": 1.0,
    },
    "consolidation_enabled": {"v": True, "cat": "sleep"},
    # RETRIEVAL
    "retrieval_alpha": {
        "v": 1.0,
        "cat": "retrieval",
        "learnable": True,
        "min": 0.0,
        "max": 5.0,
    },
    "retrieval_beta": {
        "v": 0.2,
        "cat": "retrieval",
        "learnable": True,
        "min": 0.0,
        "max": 1.0,
    },
    "retrieval_gamma": {
        "v": 0.1,
        "cat": "retrieval",
        "learnable": True,
        "min": 0.0,
        "max": 0.5,
    },
    "retrieval_tau": {
        "v": 0.7,
        "cat": "retrieval",
        "learnable": True,
        "min": 0.0,
        "max": 2.0,
    },
    # tau (Managed via ELASTICITY)
    # SALIENCE
    # salience_w_novelty (Managed via ELASTICITY)
    # SCORER
    # SDR
    # SEGMENT
    # TAU — ONE schedule is contracts.TAU_FLOOR / TAU_DECAY_FACTOR /
    # TAU_INTERVAL (W3). Mode/rate twins deleted with the linear/exponential
    # anneal branches (DEBT-009).
    # Must match contracts.TAU_FLOOR (single floor, W3 / DEF-05).
    # BRAIN
    "use_drift_monitor": {"v": False, "cat": "brain"},
    "use_exec_controller": {"v": False, "cat": "brain"},
    "use_focus_state": {"v": True, "cat": "brain"},
    # GRAPH
    "use_graph_augment": {"v": False, "cat": "graph"},
    # HRR
    "use_hrr": {"v": False, "cat": "hrr"},
    # BRAIN
    "use_meta_brain": {"v": False, "cat": "brain"},
    # CIRCUIT
    "use_microcircuits": {"v": False, "cat": "circuit"},
    # PLANNER
    "use_planner": {"v": False, "cat": "planner"},
    # SDR
    "use_sdr_prefilter": {"v": False, "cat": "sdr"},
    # SALIENCE
    # UTILITY
    # WM
    # BRAIN
    # write_daily_limit (Managed via RESOURCE)
}


def get(key: str, tenant: str) -> Any:
    """Read a brain knob. *tenant* is required (T-5) — there is no default."""
    return BrainSetting.get(key, tenant)


def set(key: str, value: Any, tenant: str) -> None:
    """Write a brain knob. *tenant* is required (T-5) — there is no default."""
    BrainSetting.set(key, value, tenant)
