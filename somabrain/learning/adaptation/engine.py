"""Lightweight adaptation engine for utility/retrieval weights.

Architecture:
    Uses DI container for state management. Per-tenant configuration override
    caching is handled by the TenantOverridesCache in tenant_cache.py.

Decomposition:
    - Config dataclasses: somabrain/learning/config.py
    - Tenant cache: somabrain/learning/tenant_cache.py
    - Annealing/entropy: somabrain/learning/annealing.py
    - Persistence: somabrain/learning/persistence.py
"""

from __future__ import annotations

from dataclasses import asdict, replace
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from somabrain.feedback import Feedback

try:
    from django.conf import settings
except Exception:  # pragma: no cover - optional dependency
    settings = None

from somabrain.learning.annealing import (
    apply_tau_annealing,
    apply_tau_decay,
    check_entropy_cap,
    exponential_decay,
    linear_decay,
)
from somabrain.learning.config import (
    AdaptationConstraints,
    AdaptationGains,
    UtilityWeights,
)
from somabrain.learning.persistence import (
    get_redis,
    is_persistence_enabled,
    load_state,
    persist_state,
)
from somabrain.learning.tenant_cache import get_tenant_override as _get_tenant_override

from .types import RetrievalWeights
from .utils import clamp as _clamp
from .history import HistoryManager
from .metrics import update_metrics


class AdaptationEngine:
    """Applies simple online updates to retrieval/utility weights."""

    def __init__(
        self,
        retrieval: RetrievalWeights | None = None,
        utility: Optional[UtilityWeights] = None,
        learning_rate: Optional[float] = None,
        max_history: Optional[int] = None,
        constraints: AdaptationConstraints | dict | None = None,
        tenant_id: Optional[str] = None,
        enable_dynamic_lr: bool = False,
        gains: Optional[AdaptationGains] = None,
    ) -> None:
        """Initialize the instance."""

        if retrieval is None:
            from somabrain.brain_settings.models import BrainSetting
            from somabrain.context.builder import RetrievalWeights as RW

            # NO MAGIC NUMBERS: use brain_settings DB
            tid = tenant_id or "default"
            retrieval = RW(
                BrainSetting.get("retrieval_alpha", tid),
                BrainSetting.get("retrieval_beta", tid),
                BrainSetting.get("retrieval_gamma", tid),
                BrainSetting.get("retrieval_tau", tid),
            )
        self._retrieval = retrieval
        self._utility = utility or UtilityWeights()
        from somabrain.brain_settings.models import BrainSetting

        tid = tenant_id or "default"
        lr = (
            learning_rate
            if learning_rate is not None
            else BrainSetting.get("adapt_lr", tid)
        )
        self._lr = lr
        self._base_lr = lr

        max_h = int(
            max_history
            if max_history is not None
            else BrainSetting.get("adapt_max_history", tid)
        )
        self._history = HistoryManager(max_h)

        self._constraint_bounds = self._init_constraints(constraints)
        self._constraints = self._build_constraints_dict(self._constraint_bounds)
        self._feedback_count = 0
        self._tenant_id = tenant_id or "default"
        self._redis = get_redis()
        self._enable_dynamic_lr = self._init_dynamic_lr(enable_dynamic_lr)
        self._gains = gains or AdaptationGains.from_settings()
        self._init_tau_metric()
        self._maybe_load_state()

    def _init_constraints(
        self, constraints: AdaptationConstraints | dict | None
    ) -> AdaptationConstraints:
        """Execute init constraints."""

        if isinstance(constraints, AdaptationConstraints):
            return constraints
        elif isinstance(constraints, dict) and constraints:
            constraint_bounds = AdaptationConstraints.from_settings()
            attr_map = {
                "alpha": ("alpha_min", "alpha_max"),
                "gamma": ("gamma_min", "gamma_max"),
                "lambda_": ("lambda_min", "lambda_max"),
                "mu": ("mu_min", "mu_max"),
                "nu": ("nu_min", "nu_max"),
            }
            for key, (lower, upper) in constraints.items():
                if key in attr_map:
                    constraint_bounds = replace(
                        constraint_bounds,
                        **{
                            attr_map[key][0]: float(lower),
                            attr_map[key][1]: float(upper),
                        },
                    )
            return constraint_bounds
        return AdaptationConstraints.from_settings()

    def _build_constraints_dict(self, bounds: AdaptationConstraints) -> dict:
        """Execute build constraints dict."""

        return {
            "alpha": (bounds.alpha_min, bounds.alpha_max),
            "gamma": (bounds.gamma_min, bounds.gamma_max),
            "lambda_": (bounds.lambda_min, bounds.lambda_max),
            "mu": (bounds.mu_min, bounds.mu_max),
            "nu": (bounds.nu_min, bounds.nu_max),
        }

    def _init_dynamic_lr(self, enable_dynamic_lr: bool) -> bool:
        """Execute init dynamic lr."""

        dyn_lr = bool(enable_dynamic_lr)
        if settings is not None:
            try:
                dyn_lr = dyn_lr or bool(
                    getattr(settings, "learning_rate_dynamic", False)
                )
            except Exception:
                pass
        else:
            try:
                from somabrain import runtime_config as _rt

                dyn_lr = dyn_lr or _rt.get_bool("learning_rate_dynamic", False)
            except Exception:
                pass
        return dyn_lr

    def _init_tau_metric(self) -> None:
        """Execute init tau metric."""

        try:
            from somabrain.metrics import tau_gauge

            offset = (hash(self._tenant_id) % 100) / 1000.0
            tau_gauge.labels(tenant_id=self._tenant_id).set(
                self._retrieval.tau + offset
            )
        except Exception:
            pass

    def _maybe_load_state(self) -> None:
        """Execute maybe load state."""

        if (
            self._redis
            and self._tenant_id
            and is_persistence_enabled()
        ):
            self._load_state()

    def set_constraints(self, constraints: AdaptationConstraints) -> None:
        """Set constraints."""
        self._constraint_bounds = constraints
        self._constraints = self._build_constraints_dict(constraints)

    def set_gains(self, gains: AdaptationGains) -> None:
        """Set gains."""
        self._gains = gains

    def set_base_learning_rate(self, base_lr: float) -> None:
        """Set base learning rate."""

        try:
            self._base_lr = float(base_lr)
        except Exception:
            return
        self._lr = self._base_lr

    def reset(
        self,
        retrieval_defaults: Optional[RetrievalWeights] = None,
        utility_defaults: Optional[UtilityWeights] = None,
        base_lr: Optional[float] = None,
        clear_history: bool = True,
    ) -> None:
        """Execute reset."""

        if retrieval_defaults is not None:
            self._retrieval.alpha, self._retrieval.beta = (
                float(retrieval_defaults.alpha),
                float(retrieval_defaults.beta),
            )
            self._retrieval.gamma, self._retrieval.tau = (
                float(retrieval_defaults.gamma),
                float(retrieval_defaults.tau),
            )
        else:
            try:
                from somabrain.context.builder import RetrievalWeights as _RW

                rw = _RW()
                self._retrieval.alpha, self._retrieval.beta = (
                    float(rw.alpha),
                    float(rw.beta),
                )
                self._retrieval.gamma, self._retrieval.tau = (
                    float(rw.gamma),
                    float(rw.tau),
                )
            except Exception:
                (
                    self._retrieval.alpha,
                    self._retrieval.beta,
                    self._retrieval.gamma,
                    self._retrieval.tau,
                ) = (1.0, 0.2, 0.1, 0.7)
        if utility_defaults is not None:
            self._utility.lambda_, self._utility.mu, self._utility.nu = (
                float(utility_defaults.lambda_),
                float(utility_defaults.mu),
                float(utility_defaults.nu),
            )
        else:
            self._utility.lambda_, self._utility.mu, self._utility.nu = 1.0, 0.1, 0.05
        if base_lr is not None:
            self.set_base_learning_rate(float(base_lr))
        else:
            self._lr = self._base_lr
        if clear_history:
            self._history.clear()
            self._feedback_count = 0
        self._persist_state()

    def save_state(self) -> None:
        """Execute save state."""
        self._persist_state()

    def load_state(self) -> dict:
        """Execute load state."""
        self._load_state()
        return self._state

    @property
    def _state(self) -> dict:
        """Execute state."""

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

    @property
    def retrieval_weights(self) -> RetrievalWeights:
        """Execute retrieval weights."""
        return self._retrieval

    @property
    def utility_weights(self) -> UtilityWeights:
        """Execute utility weights."""
        return self._utility

    @property
    def tenant_id(self) -> str:
        """Execute tenant id."""
        return self._tenant_id

    @property
    def learning_rate(self) -> float:
        """Execute learning rate."""
        return float(getattr(self, "_lr", self._base_lr))

    @property
    def tau(self) -> float:
        """Execute tau."""
        return float(self._retrieval.tau)

    @property
    def alpha(self) -> float:
        """Execute alpha."""
        return float(self._retrieval.alpha)

    def apply_feedback(
        self, utility: float | Feedback, reward: Optional[float] = None
    ) -> bool:
        """Execute apply feedback."""

        if hasattr(utility, "score"):
            utility_val = float(getattr(utility, "score"))
        else:
            utility_val = float(utility)
        signal = reward if reward is not None else utility_val
        if signal is None:
            return False
        self._update_learning_rate()
        self._history.save(self._retrieval, self._utility)
        semantic_signal, utility_signal = (
            float(signal),
            (float(reward) if reward is not None else float(signal)),
        )
        self._apply_weight_updates(semantic_signal, utility_signal)
        self._apply_tau_and_entropy()
        try:
            self._feedback_count = getattr(self, "_feedback_count", 0) + 1
        except Exception:
            pass
        self._persist_if_enabled()
        self._update_metrics()
        return True

    def _update_learning_rate(self) -> None:
        """Execute update learning rate."""

        dyn_lr_active = (
            self._enable_dynamic_lr and self._gains == AdaptationGains.from_settings()
        )
        if dyn_lr_active:
            dopamine = self._get_dopamine_level()
            lr_scale = min(max(0.5 + dopamine, 0.5), 1.2)
            self._lr = self._base_lr * lr_scale
        else:
            self._lr = self._base_lr
        self._lr_eff = self._lr

    def _apply_weight_updates(
        self, semantic_signal: float, utility_signal: float
    ) -> None:
        """Execute apply weight updates."""

        self._retrieval.alpha = self._constrain(
            "alpha",
            self._retrieval.alpha + self._lr * self._gains.alpha * semantic_signal,
        )
        self._retrieval.gamma = self._constrain(
            "gamma",
            self._retrieval.gamma + self._lr * self._gains.gamma * semantic_signal,
        )
        self._utility.lambda_ = self._constrain(
            "lambda_",
            self._utility.lambda_ + self._lr * self._gains.lambda_ * utility_signal,
        )
        self._utility.mu = self._constrain(
            "mu", self._utility.mu + self._lr * self._gains.mu * utility_signal
        )
        self._utility.nu = self._constrain(
            "nu", self._utility.nu + self._lr * self._gains.nu * utility_signal
        )
        self._utility.clamp(
            lambda_bounds=self._constraints["lambda_"],
            mu_bounds=self._constraints["mu"],
            nu_bounds=self._constraints["nu"],
        )

    def _apply_tau_and_entropy(self) -> None:
        """Execute apply tau and entropy."""

        if (
            not hasattr(self, "_tenant_override")
            or getattr(self, "_tenant_override_id", None) != self._tenant_id
        ):
            self._tenant_override = _get_tenant_override(self._tenant_id)
            self._tenant_override_id = self._tenant_id
        new_tau, was_annealed = apply_tau_annealing(
            self._retrieval.tau,
            self._tenant_id,
            getattr(self, "_feedback_count", 0),
            self._tenant_override,
        )
        self._retrieval.tau = new_tau
        self._retrieval.tau = apply_tau_decay(
            self._retrieval.tau,
            self._tenant_id,
            self._tenant_override,
            skip_if_annealed=True,
            was_annealed=was_annealed,
        )
        # INTEGRAL: check_entropy_cap now returns sharpened weights, never crashes
        (
            self._retrieval.alpha,
            self._retrieval.beta,
            self._retrieval.gamma,
            self._retrieval.tau,
            _was_sharpened,
        ) = check_entropy_cap(
            self._retrieval.alpha,
            self._retrieval.beta,
            self._retrieval.gamma,
            self._retrieval.tau,
            self._tenant_id,
        )

    def _get_dopamine_level(self) -> float:
        """Execute get dopamine level."""

        try:
            from somabrain.apps.brain.neuromodulators import PerTenantNeuromodulators

            return PerTenantNeuromodulators().get_state(self._tenant_id).dopamine
        except Exception:
            return 0.0

    def _constrain(self, name: str, value: float) -> float:
        """Execute constrain."""

        lower, upper = self._constraints.get(name, (None, None))
        if lower is not None and value < lower:
            return lower
        if upper is not None and value > upper:
            return upper
        return value

    def rollback(self) -> bool:
        """Execute rollback."""
        return self._history.rollback(self._retrieval, self._utility)

    def _update_metrics(self) -> None:
        """Execute update metrics."""
        update_metrics(self._tenant_id, self._retrieval, self._utility, self._gains, self._constraint_bounds)

    def _persist_if_enabled(self) -> None:
        """Execute persist if enabled."""

        if is_persistence_enabled():
            self._redis = get_redis()
            self._persist_state()

    def _persist_state(self) -> None:
        """Execute persist state."""

        persist_state(
            self._redis,
            self._tenant_id,
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
            getattr(self, "_feedback_count", 0),
            float(self._lr),
        )

    def _load_state(self) -> None:
        """Execute load state."""

        state = load_state(self._redis, self._tenant_id)
        if not state:
            return
        if "retrieval" in state:
            r = state["retrieval"]
            self._retrieval.alpha, self._retrieval.beta = (
                r.get("alpha", self._retrieval.alpha),
                r.get("beta", self._retrieval.beta),
            )
            self._retrieval.gamma, self._retrieval.tau = (
                r.get("gamma", self._retrieval.gamma),
                r.get("tau", self._retrieval.tau),
            )
        if "utility" in state:
            u = state["utility"]
            self._utility.lambda_, self._utility.mu, self._utility.nu = (
                u.get("lambda_", self._utility.lambda_),
                u.get("mu", self._utility.mu),
                u.get("nu", self._utility.nu),
            )
        self._feedback_count = state.get("feedback_count", 0)
        self._lr = state.get("learning_rate", self._base_lr)

    def optimize_hyperparameters(self, search_space: dict, n_trials: int = 10) -> dict:
        """Execute optimize hyperparameters."""

        lr_opts, tau_opts = (
            list(search_space.get("learning_rate", [self._base_lr])),
            list(search_space.get("tau", [self._retrieval.tau])),
        )
        return {"learning_rate": float(lr_opts[0]), "tau": float(tau_opts[0])}

    def transfer_parameters(self, source_task: str, target_task: str) -> None:
        """Execute transfer parameters."""
        self._task_type = str(target_task)

    def set_curriculum_stage(self, stage: str) -> None:
        """Set curriculum stage."""

        key, base = str(stage).strip().lower(), float(self._base_lr)
        if key == "easy":
            self._lr = _clamp(base * 1.2, 0.001, 1.0)
        elif key == "hard":
            self._lr = _clamp(base * 0.5, 0.001, 1.0)
        else:
            self._lr = _clamp(base, 0.001, 1.0)

    def _monitor_performance(self, metrics: dict) -> None:
        """Execute monitor performance."""

        try:
            performance_history = getattr(self, "performance_history", [])
            performance_history.append(dict(metrics))
            self.performance_history = performance_history
            reward = (
                float(metrics.get("reward", 0.0)) if isinstance(metrics, dict) else 0.0
            )
            self.apply_feedback(utility=reward, reward=reward)
        except Exception:
            pass

    def update_parameters(self, feedback: dict) -> None:
        """Execute update parameters."""

        reward, error = 0.0, 0.0
        try:
            reward = float(feedback.get("reward", 0.0))
        except Exception:
            pass
        try:
            error = float(feedback.get("error", 0.0))
        except Exception:
            pass
        try:
            self.apply_feedback(utility=reward, reward=reward)
            self._retrieval.tau = _clamp(
                self._retrieval.tau * (1.0 - 0.05 * error), 0.01, 10.0
            )
        except Exception:
            pass

    def update_from_experience(self, exp: dict) -> None:
        """Execute update from experience."""

        try:
            self.total_experiences = int(getattr(self, "total_experiences", 0) + 1)
        except Exception:
            self.total_experiences = 1
        try:
            reward = float(exp.get("reward", 0.0)) if isinstance(exp, dict) else 0.0
            self.apply_feedback(utility=reward, reward=reward)
        except Exception:
            pass

    def initialize_from_prior(self, prior_params: dict) -> None:
        """Execute initialize from prior."""

        if not isinstance(prior_params, dict):
            return
        try:
            self._lr = float(prior_params.get("learning_rate", self._lr))
        except Exception:
            pass
        try:
            self._retrieval.tau = float(prior_params.get("tau", self._retrieval.tau))
        except Exception:
            pass

    def linear_decay(self, tau_0: float, tau_min: float, alpha: float, t: int) -> float:
        """Execute linear decay."""
        return linear_decay(tau_0, tau_min, alpha, t)

    def exponential_decay(self, tau_0: float, gamma: float, t: int) -> float:
        """Execute exponential decay."""
        return exponential_decay(tau_0, gamma, t)
