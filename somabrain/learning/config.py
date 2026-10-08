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


def _setting(name: str, default: float | None = None) -> float:
    """Read a numeric **managed** Django setting.

    Call sites pass only a settings key. The value lives in
    ``somabrain/settings/`` (env-backed). Math contracts are that module's
    default — never a literal at a call site.
    """
    if settings is None:
        if default is None:
            raise RuntimeError(f"{name} is required (Django settings not loaded)")
        return float(default)
    try:
        value = getattr(settings, name)
    except Exception:
        if default is None:
            raise RuntimeError(f"{name} is not configured") from None
        return float(default)
    if value is None:
        if default is None:
            raise RuntimeError(f"{name} is not configured")
        return float(default)
    try:
        return float(value)
    except (TypeError, ValueError):
        if default is None:
            raise RuntimeError(f"{name} is not a number") from None
        return float(default)


@dataclass
class UtilityWeights:
    """Weights for utility trade-off calculations.

    Attributes:
        lambda_: Primary utility weight (default from settings or 1.0)
        mu: Secondary utility weight (default from settings or 0.1)
        nu: Tertiary utility weight (default from settings or 0.05)
    """

    lambda_: float = _setting("SOMABRAIN_UTILITY_LAMBDA")
    mu: float = _setting("SOMABRAIN_UTILITY_MU")
    nu: float = _setting("SOMABRAIN_UTILITY_NU")

    def clamp(
        self,
        lambda_bounds: tuple[float, float] | None = None,
        mu_bounds: tuple[float, float] | None = None,
        nu_bounds: tuple[float, float] | None = None,
    ) -> None:
        """Clamp all weights to their respective bounds."""
        if lambda_bounds is None:
            lambda_bounds = (
                _setting("SOMABRAIN_ADAPTATION_LAMBDA_MIN"),
                _setting("SOMABRAIN_ADAPTATION_LAMBDA_MAX"),
            )
        if mu_bounds is None:
            mu_bounds = (
                _setting("SOMABRAIN_ADAPTATION_MU_MIN"),
                _setting("SOMABRAIN_ADAPTATION_MU_MAX"),
            )
        if nu_bounds is None:
            nu_bounds = (
                _setting("SOMABRAIN_ADAPTATION_NU_MIN"),
                _setting("SOMABRAIN_ADAPTATION_NU_MAX"),
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

    alpha: float = _setting("SOMABRAIN_ADAPTATION_GAIN_ALPHA")
    gamma: float = _setting("SOMABRAIN_ADAPTATION_GAIN_GAMMA")
    lambda_: float = _setting("SOMABRAIN_ADAPTATION_GAIN_LAMBDA")
    mu: float = _setting("SOMABRAIN_ADAPTATION_GAIN_MU")
    nu: float = _setting("SOMABRAIN_ADAPTATION_GAIN_NU")

    @classmethod
    def from_settings(cls) -> AdaptationGains:
        """Construct gains from centralized settings only."""
        return cls(
            alpha=_setting("SOMABRAIN_ADAPTATION_GAIN_ALPHA"),
            gamma=_setting("SOMABRAIN_ADAPTATION_GAIN_GAMMA"),
            lambda_=_setting("SOMABRAIN_ADAPTATION_GAIN_LAMBDA"),
            mu=_setting("SOMABRAIN_ADAPTATION_GAIN_MU"),
            nu=_setting("SOMABRAIN_ADAPTATION_GAIN_NU"),
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

    alpha_min: float = _setting("SOMABRAIN_ADAPTATION_ALPHA_MIN")
    alpha_max: float = _setting("SOMABRAIN_ADAPTATION_ALPHA_MAX")
    gamma_min: float = _setting("SOMABRAIN_ADAPTATION_GAMMA_MIN")
    gamma_max: float = _setting("SOMABRAIN_ADAPTATION_GAMMA_MAX")
    lambda_min: float = _setting("SOMABRAIN_ADAPTATION_LAMBDA_MIN")
    lambda_max: float = _setting("SOMABRAIN_ADAPTATION_LAMBDA_MAX")
    mu_min: float = _setting("SOMABRAIN_ADAPTATION_MU_MIN")
    mu_max: float = _setting("SOMABRAIN_ADAPTATION_MU_MAX")
    nu_min: float = _setting("SOMABRAIN_ADAPTATION_NU_MIN")
    nu_max: float = _setting("SOMABRAIN_ADAPTATION_NU_MAX")

    @classmethod
    def from_settings(cls) -> AdaptationConstraints:
        """Construct constraints from centralized settings only."""
        return cls(
            alpha_min=_setting("SOMABRAIN_ADAPTATION_ALPHA_MIN"),
            alpha_max=_setting("SOMABRAIN_ADAPTATION_ALPHA_MAX"),
            gamma_min=_setting("SOMABRAIN_ADAPTATION_GAMMA_MIN"),
            gamma_max=_setting("SOMABRAIN_ADAPTATION_GAMMA_MAX"),
            lambda_min=_setting("SOMABRAIN_ADAPTATION_LAMBDA_MIN"),
            lambda_max=_setting("SOMABRAIN_ADAPTATION_LAMBDA_MAX"),
            mu_min=_setting("SOMABRAIN_ADAPTATION_MU_MIN"),
            mu_max=_setting("SOMABRAIN_ADAPTATION_MU_MAX"),
            nu_min=_setting("SOMABRAIN_ADAPTATION_NU_MIN"),
            nu_max=_setting("SOMABRAIN_ADAPTATION_NU_MAX"),
        )
