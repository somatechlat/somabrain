"""Configuration dataclasses for the adaptation engine.

Defaults come from ``somabrain.math.contracts`` — the single math-contract
source (W1.1).  Settings may override; the contract values are the baseline.

Dataclasses:
- UtilityWeights: Trade-off weights for utility calculations
- AdaptationGains: Per-parameter gains applied to learning signals
- AdaptationConstraints: Bounds for parameter values during adaptation
"""

from __future__ import annotations

from dataclasses import dataclass

from somabrain.math.contracts import ADAPT_BOUNDS, ADAPT_GAINS

try:
    from django.conf import settings
except Exception:  # pragma: no cover - optional dependency
    settings = None


def _setting(name: str, default: float) -> float:
    """Read a numeric Django setting, falling back to ``default``.

    Django's ``LazySettings`` is always truthy, so ``getattr(settings, …) if
    settings else default`` raises ``ImproperlyConfigured`` when the settings
    module is not booted. Resolve lazily and treat any failure as "unset".
    """
    if settings is None:
        return default
    try:
        value = getattr(settings, name)
    except Exception:
        return default
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


@dataclass
class UtilityWeights:
    """Weights for utility trade-off calculations.

    Attributes:
        lambda_: Primary utility weight (default from settings or 1.0)
        mu: Secondary utility weight (default from settings or 0.1)
        nu: Tertiary utility weight (default from settings or 0.05)
    """

    lambda_: float = _setting("SOMABRAIN_UTILITY_LAMBDA", 1.0)
    mu: float = _setting("SOMABRAIN_UTILITY_MU", 0.1)
    nu: float = _setting("SOMABRAIN_UTILITY_NU", 0.05)

    def clamp(
        self,
        lambda_bounds: tuple[float, float] | None = None,
        mu_bounds: tuple[float, float] | None = None,
        nu_bounds: tuple[float, float] | None = None,
    ) -> None:
        """Clamp all weights to their respective bounds."""
        if lambda_bounds is None:
            lambda_bounds = (
                _setting("UTILITY_LAMBDA_MIN", 0.0),
                _setting("UTILITY_LAMBDA_MAX", 5.0),
            )
        if mu_bounds is None:
            mu_bounds = (
                _setting("UTILITY_MU_MIN", 0.0),
                _setting("UTILITY_MU_MAX", 5.0),
            )
        if nu_bounds is None:
            nu_bounds = (
                _setting("UTILITY_NU_MIN", 0.0),
                _setting("UTILITY_NU_MAX", 5.0),
            )
        self.lambda_ = min(max(self.lambda_, lambda_bounds[0]), lambda_bounds[1])
        self.mu = min(max(self.mu, mu_bounds[0]), mu_bounds[1])
        self.nu = min(max(self.nu, nu_bounds[0]), nu_bounds[1])


@dataclass(frozen=True)
class AdaptationGains:
    """Per-parameter gains applied to the learning signal.

    Defaults from ``somabrain.math.contracts.ADAPT_GAINS`` (single source).
    Positive gains increase the parameter on positive feedback; negative
    gains decrease it.  γ/μ/ν are negative by design.

    Attributes:
        alpha: Gain for retrieval alpha parameter
        gamma: Gain for retrieval gamma parameter
        lambda_: Gain for utility lambda parameter
        mu: Gain for utility mu parameter
        nu: Gain for utility nu parameter
    """

    alpha: float = _setting("SOMABRAIN_ADAPTATION_GAIN_ALPHA", ADAPT_GAINS["alpha"])
    gamma: float = _setting("SOMABRAIN_ADAPTATION_GAIN_GAMMA", ADAPT_GAINS["gamma"])
    lambda_: float = _setting("SOMABRAIN_ADAPTATION_GAIN_LAMBDA", ADAPT_GAINS["lambda_"])
    mu: float = _setting("SOMABRAIN_ADAPTATION_GAIN_MU", ADAPT_GAINS["mu"])
    nu: float = _setting("SOMABRAIN_ADAPTATION_GAIN_NU", ADAPT_GAINS["nu"])

    @classmethod
    def from_settings(cls) -> AdaptationGains:
        """Construct gains from centralized settings only."""
        return cls(
            alpha=_setting("SOMABRAIN_ADAPTATION_GAIN_ALPHA", ADAPT_GAINS["alpha"]),
            gamma=_setting("SOMABRAIN_ADAPTATION_GAIN_GAMMA", ADAPT_GAINS["gamma"]),
            lambda_=_setting("SOMABRAIN_ADAPTATION_GAIN_LAMBDA", ADAPT_GAINS["lambda_"]),
            mu=_setting("SOMABRAIN_ADAPTATION_GAIN_MU", ADAPT_GAINS["mu"]),
            nu=_setting("SOMABRAIN_ADAPTATION_GAIN_NU", ADAPT_GAINS["nu"]),
        )


@dataclass(frozen=True)
class AdaptationConstraints:
    """Bounds for parameter values during adaptation.

    Defaults from ``somabrain.math.contracts.ADAPT_BOUNDS`` (single source).
    These constraints prevent parameters from drifting too far from reasonable
    values during online learning.

    Attributes:
        alpha_min/max: Bounds for retrieval alpha
        gamma_min/max: Bounds for retrieval gamma
        lambda_min/max: Bounds for utility lambda
        mu_min/max: Bounds for utility mu
        nu_min/max: Bounds for utility nu
    """

    alpha_min: float = _setting("SOMABRAIN_ADAPTATION_ALPHA_MIN", ADAPT_BOUNDS["alpha"][0])
    alpha_max: float = _setting("SOMABRAIN_ADAPTATION_ALPHA_MAX", ADAPT_BOUNDS["alpha"][1])
    gamma_min: float = _setting("SOMABRAIN_ADAPTATION_GAMMA_MIN", ADAPT_BOUNDS["gamma"][0])
    gamma_max: float = _setting("SOMABRAIN_ADAPTATION_GAMMA_MAX", ADAPT_BOUNDS["gamma"][1])
    lambda_min: float = _setting("SOMABRAIN_ADAPTATION_LAMBDA_MIN", ADAPT_BOUNDS["lambda_"][0])
    lambda_max: float = _setting("SOMABRAIN_ADAPTATION_LAMBDA_MAX", ADAPT_BOUNDS["lambda_"][1])
    mu_min: float = _setting("SOMABRAIN_ADAPTATION_MU_MIN", ADAPT_BOUNDS["mu"][0])
    mu_max: float = _setting("SOMABRAIN_ADAPTATION_MU_MAX", ADAPT_BOUNDS["mu"][1])
    nu_min: float = _setting("SOMABRAIN_ADAPTATION_NU_MIN", ADAPT_BOUNDS["nu"][0])
    nu_max: float = _setting("SOMABRAIN_ADAPTATION_NU_MAX", ADAPT_BOUNDS["nu"][1])

    @classmethod
    def from_settings(cls) -> AdaptationConstraints:
        """Construct constraints from centralized settings only."""
        return cls(
            alpha_min=_setting("SOMABRAIN_ADAPTATION_ALPHA_MIN", ADAPT_BOUNDS["alpha"][0]),
            alpha_max=_setting("SOMABRAIN_ADAPTATION_ALPHA_MAX", ADAPT_BOUNDS["alpha"][1]),
            gamma_min=_setting("SOMABRAIN_ADAPTATION_GAMMA_MIN", ADAPT_BOUNDS["gamma"][0]),
            gamma_max=_setting("SOMABRAIN_ADAPTATION_GAMMA_MAX", ADAPT_BOUNDS["gamma"][1]),
            lambda_min=_setting("SOMABRAIN_ADAPTATION_LAMBDA_MIN", ADAPT_BOUNDS["lambda_"][0]),
            lambda_max=_setting("SOMABRAIN_ADAPTATION_LAMBDA_MAX", ADAPT_BOUNDS["lambda_"][1]),
            mu_min=_setting("SOMABRAIN_ADAPTATION_MU_MIN", ADAPT_BOUNDS["mu"][0]),
            mu_max=_setting("SOMABRAIN_ADAPTATION_MU_MAX", ADAPT_BOUNDS["mu"][1]),
            nu_min=_setting("SOMABRAIN_ADAPTATION_NU_MIN", ADAPT_BOUNDS["nu"][0]),
            nu_max=_setting("SOMABRAIN_ADAPTATION_NU_MAX", ADAPT_BOUNDS["nu"][1]),
        )
