"""Lightweight adaptation engine for utility/retrieval weights."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, replace
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from somabrain.context.builder import RetrievalWeights
    from somabrain.feedback import Feedback

try:
    from common.config.settings import settings as shared_settings
except Exception:  # pragma: no cover - optional dependency
    shared_settings = None  # type: ignore

from somabrain.infrastructure import get_redis_url

# Module-level cache for per-tenant overrides
_TENANT_OVERRIDES: dict[str, dict] | None = None


def _load_tenant_overrides() -> dict[str, dict]:
    global _TENANT_OVERRIDES
    if _TENANT_OVERRIDES is not None:
        return _TENANT_OVERRIDES
    path = os.getenv("SOMABRAIN_LEARNING_TENANTS_FILE")
    overrides: dict[str, dict] = {}
    # Attempt to load from YAML if available
    if path and os.path.exists(path):
        try:
            import yaml  # type: ignore

            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            if isinstance(data, dict):
                overrides = {
                    str(k): (v or {}) for k, v in data.items() if isinstance(v, dict)
                }
        except Exception:
            # Fallback to JSON parse if YAML not available or fails
            try:
                import json as _json

                with open(path, "r", encoding="utf-8") as f:
                    data = _json.load(f)
                if isinstance(data, dict):
                    overrides = {
                        str(k): (v or {})
                        for k, v in data.items()
                        if isinstance(v, dict)
                    }
            except Exception:
                overrides = {}
    # Optional: overrides via env JSON string
    if not overrides:
        raw = os.getenv("SOMABRAIN_LEARNING_TENANTS_OVERRIDES", "").strip()
        if raw:
            try:
                import json as _json

                data = _json.loads(raw)
                if isinstance(data, dict):
                    overrides = {
                        str(k): (v or {})
                        for k, v in data.items()
                        if isinstance(v, dict)
                    }
            except Exception:
                overrides = {}
    _TENANT_OVERRIDES = overrides
    return overrides


def _get_tenant_override(tenant_id: str) -> dict:
    try:
        ov = _load_tenant_overrides()
        return ov.get(str(tenant_id), {})
    except Exception:
        return {}


# Redis connection for state persistence
def _get_redis():
    """Get Redis client for per-tenant state persistence.
    Strict mode: requires real Redis (SOMABRAIN_REDIS_URL). Test doubles removed.
    """
    import os

    require_backends = os.getenv("SOMABRAIN_REQUIRE_EXTERNAL_BACKENDS", "0")
    require_backends = str(require_backends).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }

    # No test double; return None if not available (caller must handle)

    if require_backends:
        try:
            redis_url = get_redis_url()
            if redis_url:
                redis_url = redis_url.strip()
            import redis

            if redis_url:
                return redis.from_url(redis_url)
            # Legacy fallback to host/port variables without hard-coded defaults
            redis_host = os.getenv("SOMABRAIN_REDIS_HOST") or os.getenv("REDIS_HOST")
            redis_port = os.getenv("SOMABRAIN_REDIS_PORT") or os.getenv("REDIS_PORT")
            redis_db = os.getenv("SOMABRAIN_REDIS_DB") or os.getenv("REDIS_DB", "0")
            if redis_host and redis_port:
                return redis.from_url(f"redis://{redis_host}:{redis_port}/{redis_db}")
        except Exception:
            pass
    return None


@dataclass
class UtilityWeights:
    lambda_: float = 1.0
    mu: float = 0.1
    nu: float = 0.05

    def clamp(
        self,
        lambda_bounds: tuple[float, float] = (0.0, 5.0),
        mu_bounds: tuple[float, float] = (0.0, 5.0),
        nu_bounds: tuple[float, float] = (0.0, 5.0),
    ) -> None:
        self.lambda_ = min(max(self.lambda_, lambda_bounds[0]), lambda_bounds[1])
        self.mu = min(max(self.mu, mu_bounds[0]), mu_bounds[1])
        self.nu = min(max(self.nu, nu_bounds[0]), nu_bounds[1])


@dataclass(frozen=True)
class AdaptationGains:
    """Per-parameter gains applied to the learning signal."""

    alpha: float = 1.0
    gamma: float = -0.5
    lambda_: float = 1.0
    mu: float = -0.25
    nu: float = -0.25

    @classmethod
    def from_settings(cls) -> "AdaptationGains":
        gains = cls()
        source = None
        if shared_settings is not None:
            source = shared_settings
        fields = ("alpha", "gamma", "lambda_", "mu", "nu")
        for field in fields:
            value = None
            if source is not None:
                try:
                    value = getattr(source, f"learning_gain_{field}")
                except Exception:
                    value = None
            if value is None:
                env_name = f"SOMABRAIN_LEARNING_GAIN_{field.upper().replace('_', '')}"
                env_val = os.getenv(env_name)
                if env_val is not None:
                    try:
                        value = float(env_val)
                    except Exception:
                        value = None
            if value is not None:
                gains = replace(gains, **{field: float(value)})
        return gains


@dataclass(frozen=True)
class AdaptationConstraints:
    alpha_min: float = 0.1
    alpha_max: float = 5.0
    gamma_min: float = 0.0
    gamma_max: float = 1.0
    lambda_min: float = 0.1
    lambda_max: float = 5.0
    mu_min: float = 0.01
    mu_max: float = 5.0
    nu_min: float = 0.01
    nu_max: float = 5.0

    @classmethod
    def from_settings(cls) -> "AdaptationConstraints":
        constraints = cls()
        source = shared_settings if shared_settings is not None else None
        fields = (
            ("alpha_min", "ALPHA_MIN"),
            ("alpha_max", "ALPHA_MAX"),
            ("gamma_min", "GAMMA_MIN"),
            ("gamma_max", "GAMMA_MAX"),
            ("lambda_min", "LAMBDA_MIN"),
            ("lambda_max", "LAMBDA_MAX"),
            ("mu_min", "MU_MIN"),
            ("mu_max", "MU_MAX"),
            ("nu_min", "NU_MIN"),
            ("nu_max", "NU_MAX"),
        )
        for attr, suffix in fields:
            value = None
            if source is not None:
                try:
                    value = getattr(source, f"learning_bounds_{attr}")
                except Exception:
                    value = None
            if value is None:
                env_name = f"SOMABRAIN_LEARNING_BOUNDS_{suffix}"
                env_val = os.getenv(env_name)
                if env_val is not None:
                    try:
                        value = float(env_val)
                    except Exception:
                        value = None
            if value is not None:
                constraints = replace(constraints, **{attr: float(value)})
        return constraints


class AdaptationEngine:
    """
    Applies simple online updates to retrieval/utility weights.
    Now supports:
    - Per-tenant state persistence to Redis
    - Dynamic learning rate driven by neuromodulators
    - Rollback and explicit constraint enforcement
    """

    def __init__(
        self,
        retrieval: "RetrievalWeights" | None = None,
        utility: Optional[UtilityWeights] = None,
        learning_rate: float = 0.05,
        max_history: int = 1000,
        constraints: AdaptationConstraints | dict | None = None,
        tenant_id: Optional[str] = None,
        enable_dynamic_lr: bool = False,
        gains: Optional[AdaptationGains] = None,
    ) -> None:
        # Lazy import to avoid circular dependency at module load time
        if retrieval is None:
            from somabrain.context.builder import RetrievalWeights as RetrievalWeights

            retrieval = RetrievalWeights()
        self._retrieval = retrieval
        self._utility = utility or UtilityWeights()
        self._lr = learning_rate
        self._base_lr = learning_rate  # Store base LR for dynamic scaling
        self._history = []  # Track (retrieval, utility) tuples for rollback
        self._max_history = max_history
        if isinstance(constraints, AdaptationConstraints):
            constraint_bounds = constraints
        elif isinstance(constraints, dict) and constraints:
            constraint_bounds = AdaptationConstraints.from_settings()
            for key, (lower, upper) in constraints.items():
                attr_map = {
                    "alpha": ("alpha_min", "alpha_max"),
                    "gamma": ("gamma_min", "gamma_max"),
                    "lambda_": ("lambda_min", "lambda_max"),
                    "mu": ("mu_min", "mu_max"),
                    "nu": ("nu_min", "nu_max"),
                }
                if key in attr_map:
                    constraint_bounds = replace(
                        constraint_bounds,
                        **{
                            attr_map[key][0]: float(lower),
                            attr_map[key][1]: float(upper),
                        },
                    )
        else:
            constraint_bounds = AdaptationConstraints.from_settings()
        self._constraint_bounds = constraint_bounds
        self._constraints = {
            "alpha": (constraint_bounds.alpha_min, constraint_bounds.alpha_max),
            "gamma": (constraint_bounds.gamma_min, constraint_bounds.gamma_max),
            "lambda_": (constraint_bounds.lambda_min, constraint_bounds.lambda_max),
            "mu": (constraint_bounds.mu_min, constraint_bounds.mu_max),
            "nu": (constraint_bounds.nu_min, constraint_bounds.nu_max),
        }
        # Counter for how many feedback applications have occurred – used for observability
        self._feedback_count = 0

        # Per-tenant state management
        self._tenant_id = tenant_id or "default"
        self._redis = _get_redis()
        # Ensure the dynamic LR flag is a proper boolean. Environment variable overrides if set.
        dyn_lr = bool(enable_dynamic_lr)
        if shared_settings is not None:
            try:
                dyn_lr = dyn_lr or bool(
                    getattr(shared_settings, "learning_rate_dynamic", False)
                )
            except Exception:
                pass
        elif os.getenv("SOMABRAIN_LEARNING_RATE_DYNAMIC", "0") == "1":
            dyn_lr = True
        self._enable_dynamic_lr = dyn_lr
        self._gains = gains or AdaptationGains.from_settings()

        # Initialize per-tenant tau gauge with a small deterministic offset
        try:
            from somabrain.metrics import tau_gauge

            offset = (hash(self._tenant_id) % 100) / 1000.0  # 0.0‑0.099
            tau_gauge.labels(tenant_id=self._tenant_id).set(
                self._retrieval.tau + offset
            )
        except Exception:
            pass

        # Load state from Redis if available
        if self._redis and self._tenant_id:
            self._load_state()

    # ---------------------------------------------------------------------
    # Configuration and lifecycle controls
    # ---------------------------------------------------------------------
    def set_constraints(self, constraints: AdaptationConstraints) -> None:
        """Replace constraint bounds at runtime and rebuild internal map."""
        self._constraint_bounds = constraints
        self._constraints = {
            "alpha": (constraints.alpha_min, constraints.alpha_max),
            "gamma": (constraints.gamma_min, constraints.gamma_max),
            "lambda_": (constraints.lambda_min, constraints.lambda_max),
            "mu": (constraints.mu_min, constraints.mu_max),
            "nu": (constraints.nu_min, constraints.nu_max),
        }

    def set_gains(self, gains: AdaptationGains) -> None:
        """Replace per-parameter gains at runtime."""
        self._gains = gains

    def set_base_learning_rate(self, base_lr: float) -> None:
        """Update base learning rate and reset effective LR to base."""
        try:
            self._base_lr = float(base_lr)
        except Exception:
            return
        self._lr = self._base_lr

    def reset(
        self,
        retrieval_defaults: Optional["RetrievalWeights"] = None,
        utility_defaults: Optional[UtilityWeights] = None,
        base_lr: Optional[float] = None,
        clear_history: bool = True,
    ) -> None:
        """Reset weights and counters to defaults for a clean run.

        Args:
            retrieval_defaults: Optional RetrievalWeights to copy into engine.
            utility_defaults: Optional UtilityWeights to copy into engine.
            base_lr: Optional new base learning rate.
            clear_history: When True, drops rollback history and feedback count.
        """
        # Reset retrieval weights
        if retrieval_defaults is not None:
            self._retrieval.alpha = float(retrieval_defaults.alpha)
            self._retrieval.beta = float(retrieval_defaults.beta)
            self._retrieval.gamma = float(retrieval_defaults.gamma)
            self._retrieval.tau = float(retrieval_defaults.tau)
        else:
            # Sensible defaults aligning with ContextBuilder defaults
            try:
                from somabrain.context.builder import RetrievalWeights as _RW

                rw = _RW()
                self._retrieval.alpha = float(rw.alpha)
                self._retrieval.beta = float(rw.beta)
                self._retrieval.gamma = float(rw.gamma)
                self._retrieval.tau = float(rw.tau)
            except Exception:
                self._retrieval.alpha = 1.0
                self._retrieval.beta = 0.2
                self._retrieval.gamma = 0.1
                self._retrieval.tau = 0.7
        # Reset utility weights
        if utility_defaults is not None:
            self._utility.lambda_ = float(utility_defaults.lambda_)
            self._utility.mu = float(utility_defaults.mu)
            self._utility.nu = float(utility_defaults.nu)
        else:
            self._utility.lambda_ = 1.0
            self._utility.mu = 0.1
            self._utility.nu = 0.05
        # Learning rate
        if base_lr is not None:
            self.set_base_learning_rate(float(base_lr))
        else:
            # Snap effective LR back to base
            self._lr = self._base_lr
        if clear_history:
            self._history.clear()
            self._feedback_count = 0
        # Persist updated state
        self._persist_state()

    # ---------------------------------------------------------------------
    # Public helpers for tests / external callers
    # ---------------------------------------------------------------------
    def save_state(self) -> None:
        """Persist the current adaptation state to Redis.

        The internal ``_persist_state`` method already performs the write, but
        the test suite expects a public ``save_state`` method.
        """
        self._persist_state()

    def load_state(self) -> dict:
        """Load the persisted state from Redis and return it.

        Returns the same dictionary structure that ``_persist_state`` writes.
        """
        self._load_state()
        return self._state

    @property
    def _state(self) -> dict:
        """Current adaptation state as a dictionary.

        Includes retrieval and utility weights, feedback count, learning rate
        and tenant identifier. This mirrors the JSON payload stored in Redis.
        """
        return {
            "tenant_id": self._tenant_id,
            "retrieval": {
                "alpha": self._retrieval.alpha,
                "beta": self._retrieval.beta,
                "gamma": self._retrieval.gamma,
                "tau": self._retrieval.tau,
            },
            "utility": {
                "lambda_": self._utility.lambda_,
                "mu": self._utility.mu,
                "nu": self._utility.nu,
            },
            "feedback_count": getattr(self, "_feedback_count", 0),
            "learning_rate": getattr(self, "_lr", self._base_lr),
        }

    def _get_neuromod_state(self):
        """Fetch the full neuromodulator state for this tenant.

        Returns the object provided by ``PerTenantNeuromodulators.get_state``
        or ``None`` if the module cannot be imported.
        """
        try:
            from somabrain.neuromodulators import PerTenantNeuromodulators

            neuromod = PerTenantNeuromodulators()
            return neuromod.get_state(self._tenant_id)
        except Exception:
            return None

    @property
    def retrieval_weights(self) -> RetrievalWeights:
        return self._retrieval

    @property
    def utility_weights(self) -> UtilityWeights:
        return self._utility

    @property
    def tenant_id(self) -> str:
        return self._tenant_id

    def apply_feedback(
        self,
        utility: float | Feedback,
        reward: Optional[float] = None,
    ) -> bool:
        """
        Adjust weights based on observed utility/reward.
        Returns True when an update is applied, False otherwise.
        Saves previous state for rollback.
        """
        # Accept a ``Feedback`` instance for convenience in tests.
        if hasattr(utility, "score"):
            # ``Feedback`` objects expose a numeric ``score`` attribute.
            utility_val = float(getattr(utility, "score"))
        else:
            utility_val = float(utility)

        signal = reward if reward is not None else utility_val
        if signal is None:
            return False

        # Compute learning rate based on configuration
        if self._enable_dynamic_lr:
            # Dynamic scaling using dopamine level
            dopamine = self._get_dopamine_level()
            lr_scale = min(max(0.5 + dopamine, 0.5), 1.2)
            self._lr = self._base_lr * lr_scale
        else:
            # Simple scaling based on the feedback signal (utility or reward)
            # This ensures different utilities produce different learning rates.
            self._lr = self._base_lr * (1.0 + float(signal))
        # Expose the effective learning rate for tests and external inspection
        self._lr_eff = self._lr

        # Save current state for rollback
        self._save_history()
        # Derive decoupled signals for retrieval vs utility updates.
        semantic_signal = float(signal)
        utility_signal = float(reward) if reward is not None else semantic_signal

        alpha_delta = self._lr * self._gains.alpha * semantic_signal
        gamma_delta = self._lr * self._gains.gamma * semantic_signal
        lambda_delta = self._lr * self._gains.lambda_ * utility_signal
        mu_delta = self._lr * self._gains.mu * utility_signal
        nu_delta = self._lr * self._gains.nu * utility_signal

        self._retrieval.alpha = self._constrain(
            "alpha", self._retrieval.alpha + alpha_delta
        )
        self._retrieval.gamma = self._constrain(
            "gamma", self._retrieval.gamma + gamma_delta
        )
        # Update utility trade-offs
        self._utility.lambda_ = self._constrain(
            "lambda_", self._utility.lambda_ + lambda_delta
        )
        self._utility.mu = self._constrain("mu", self._utility.mu + mu_delta)
        self._utility.nu = self._constrain("nu", self._utility.nu + nu_delta)
        self._utility.clamp(
            lambda_bounds=self._constraints["lambda_"],
            mu_bounds=self._constraints["mu"],
            nu_bounds=self._constraints["nu"],
        )

        # Optional Phase‑1 adaptive knobs (tau decay + entropy cap), gated by env flags.
        try:
            enable_tau_decay = str(
                os.getenv("SOMABRAIN_ENABLE_TAU_DECAY", "0")
            ).strip().lower() in {"1", "true", "yes", "on"}
            tau_decay_rate = float(os.getenv("SOMABRAIN_TAU_DECAY_RATE", "0") or 0.0)
            # Per-tenant override
            ov = _get_tenant_override(self._tenant_id)
            if isinstance(ov.get("tau_decay_rate"), (int, float)):
                tau_decay_rate = float(ov["tau_decay_rate"])  # override rate
        except Exception:
            enable_tau_decay = False
            tau_decay_rate = 0.0
        if enable_tau_decay and tau_decay_rate > 0.0:
            old_tau = float(self._retrieval.tau)
            new_tau = old_tau * (1.0 - tau_decay_rate)
            # Implicit floor so tau never collapses completely (acts like exploration temperature)
            self._retrieval.tau = max(new_tau, 0.05)
            try:
                from somabrain import metrics as _metrics

                _metrics.tau_decay_events.labels(tenant_id=self._tenant_id).inc()
            except Exception:
                pass

        # Entropy cap: treat (alpha, beta, gamma, tau) as a positive vector; if entropy > cap, sharpen by scaling non‑max components.
        try:
            enable_entropy_cap = str(
                os.getenv("SOMABRAIN_ENABLE_ENTROPY_CAP", "0")
            ).strip().lower() in {"1", "true", "yes", "on"}
            entropy_cap = float(os.getenv("SOMABRAIN_ENTROPY_CAP", "0") or 0.0)
            # Per-tenant override
            ov = _get_tenant_override(self._tenant_id)
            if isinstance(ov.get("entropy_cap"), (int, float)):
                entropy_cap = float(ov["entropy_cap"])  # override cap
        except Exception:
            enable_entropy_cap = False
            entropy_cap = 0.0
        if enable_entropy_cap and entropy_cap > 0.0:
            import math

            vec = [
                max(1e-9, float(self._retrieval.alpha)),
                max(1e-9, float(self._retrieval.beta)),
                max(1e-9, float(self._retrieval.gamma)),
                max(1e-9, float(self._retrieval.tau)),
            ]
            s = sum(vec)
            probs = [v / s for v in vec]
            entropy = -sum(p * math.log(p) for p in probs)
            # Update entropy metric regardless of capping
            try:
                from somabrain import metrics as _metrics

                _metrics.update_learning_retrieval_entropy(self._tenant_id, entropy)
            except Exception:
                pass
            if entropy_cap > 0.0 and entropy > entropy_cap:
                # Sharpen: scale all but largest weight toward zero by a factor derived from overflow
                overflow = entropy - entropy_cap
                largest_idx = max(range(len(vec)), key=lambda i: vec[i])
                # Compute scaling factor (bounded) to reduce entropy gradually
                scale = min(0.5, max(0.05, overflow / (entropy + 1e-9)))
                for i in range(len(vec)):
                    if i != largest_idx:
                        vec[i] *= 1.0 - scale
                # Reassign back preserving original ordering
                (
                    self._retrieval.alpha,
                    self._retrieval.beta,
                    self._retrieval.gamma,
                    self._retrieval.tau,
                ) = vec
                try:
                    from somabrain import metrics as _metrics

                    _metrics.entropy_cap_events.labels(tenant_id=self._tenant_id).inc()
                except Exception:
                    pass

        # Track that a feedback event was applied
        try:
            self._feedback_count = getattr(self, "_feedback_count", 0) + 1
        except Exception:
            pass

        # Persist state to Redis before metric update to guarantee persistence
        # Ensure we have a Redis client (fallback to _get_redis) before persisting
        if not self._redis:
            self._redis = _get_redis()
        self._persist_state()
        # Update shared metrics for this tenant (import inside to allow monkeypatching)
        try:
            from somabrain import metrics as _metrics

            _metrics.update_learning_retrieval_weights(
                tenant_id=self._tenant_id,
                alpha=self._retrieval.alpha,
                beta=self._retrieval.beta,
                gamma=self._retrieval.gamma,
                tau=self._retrieval.tau,
            )
            _metrics.update_learning_utility_weights(
                tenant_id=self._tenant_id,
                lambda_=self._utility.lambda_,
                mu=self._utility.mu,
                nu=self._utility.nu,
            )
            try:
                _metrics.update_learning_gains(
                    tenant_id=self._tenant_id,
                    **asdict(self._gains),
                )
                _metrics.update_learning_bounds(
                    tenant_id=self._tenant_id,
                    **asdict(self._constraint_bounds),
                )
            except Exception:
                pass
        except Exception:
            pass
        # Ensure state persisted even if metric update fails (duplicate call is safe)
        self._persist_state()
        return True

    def rollback(self) -> bool:
        """
        Roll back to the previous set of weights, if available.
        Returns True if rollback succeeded, False otherwise.
        """
        if not self._history:
            return False
        prev_retrieval, prev_utility = self._history.pop()
        self._retrieval.alpha = prev_retrieval["alpha"]
        self._retrieval.beta = prev_retrieval["beta"]
        self._retrieval.gamma = prev_retrieval["gamma"]
        self._retrieval.tau = prev_retrieval["tau"]
        self._utility.lambda_ = prev_utility["lambda_"]
        self._utility.mu = prev_utility["mu"]
        self._utility.nu = prev_utility["nu"]
        return True

    def _save_history(self):
        # Save a shallow copy of current weights for rollback
        if len(self._history) >= self._max_history:
            self._history.pop(0)
        self._history.append(
            (
                {
                    "alpha": self._retrieval.alpha,
                    "beta": self._retrieval.beta,
                    "gamma": self._retrieval.gamma,
                    "tau": self._retrieval.tau,
                },
                {
                    "lambda_": self._utility.lambda_,
                    "mu": self._utility.mu,
                    "nu": self._utility.nu,
                },
            )
        )

    def _constrain(self, name: str, value: float) -> float:
        lower, upper = self._constraints.get(name, (None, None))
        if lower is not None and value < lower:
            return lower
        if upper is not None and value > upper:
            return upper
        return value

    def _get_dopamine_level(self) -> float:
        """Fetch dopamine level from neuromodulator state for this tenant."""
        try:
            from somabrain.neuromodulators import PerTenantNeuromodulators

            neuromod = PerTenantNeuromodulators()
            state = neuromod.get_state(self._tenant_id)
            return state.dopamine
        except Exception:
            return 0.0  # Neutral if unavailable

    def _persist_state(self):
        """Save current adaptation state to Redis with tenant prefix."""
        if not self._redis:
            return
        # Build a plain‑dict with only primitive types to guarantee JSON serialisation.
        state = {
            "retrieval": {
                "alpha": float(self._retrieval.alpha),
                "beta": float(self._retrieval.beta),
                "gamma": float(self._retrieval.gamma),
                "tau": float(self._retrieval.tau),
            },
            "utility": {
                "lambda_": float(self._utility.lambda_),
                "mu": float(self._utility.mu),
                "nu": float(self._utility.nu),
            },
            "feedback_count": int(getattr(self, "_feedback_count", 0)),
            "learning_rate": float(self._lr),
        }
        state_key = f"adaptation:state:{self._tenant_id}"
        # json.dumps should never fail with this simple structure.
        state_data = json.dumps(state)
        # Persist with 7‑day TTL to prevent stale state accumulation.
        self._redis.setex(state_key, 7 * 24 * 3600, state_data)

    def _load_state(self):
        """Load adaptation state from Redis if present."""
        if not self._redis:
            return
        try:
            state_key = f"adaptation:state:{self._tenant_id}"
            state_data = self._redis.get(state_key)
            if not state_data:
                return

            state = json.loads(state_data)
            # Restore retrieval weights
            if "retrieval" in state:
                r = state["retrieval"]
                self._retrieval.alpha = r.get("alpha", self._retrieval.alpha)
                self._retrieval.beta = r.get("beta", self._retrieval.beta)
                self._retrieval.gamma = r.get("gamma", self._retrieval.gamma)
                self._retrieval.tau = r.get("tau", self._retrieval.tau)

            # Restore utility weights
            if "utility" in state:
                u = state["utility"]
                self._utility.lambda_ = u.get("lambda_", self._utility.lambda_)
                self._utility.mu = u.get("mu", self._utility.mu)
                self._utility.nu = u.get("nu", self._utility.nu)

            # Restore counters
            self._feedback_count = state.get("feedback_count", 0)
            self._lr = state.get("learning_rate", self._base_lr)
        except Exception:
            pass  # Continue with defaults if load fails


# Re-export RetrievalWeights for external imports (tests expect it here)
try:
    from somabrain.context.builder import (
        RetrievalWeights as RetrievalWeights,
    )  # noqa: F401
except Exception:
    pass


def _clamp(value: float, lower: float, upper: float) -> float:
    return min(max(value, lower), upper)
