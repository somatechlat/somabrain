"""Configuration dataclasses for the adaptation engine.

This module contains the configuration dataclasses used by the AdaptationEngine:
- UtilityWeights: Trade-off weights for utility calculations
- AdaptationGains: Per-parameter gains applied to learning signals
- AdaptationConstraints: Bounds for parameter values during adaptation
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

try:
    from django.conf import settings
except Exception:  # pragma: no cover - optional dependency
    settings = None


@dataclass
class UtilityWeights:
    """Weights for utility trade-off calculations.

    Attributes:
        lambda_: Primary utility weight (default from settings or 1.0)
        mu: Secondary utility weight (default from settings or 0.1)
        nu: Tertiary utility weight (default from settings or 0.05)
    """

    lambda_: float = float(
        getattr(settings, "SOMABRAIN_UTILITY_LAMBDA", 1.0) if settings else 1.0
    )
    mu: float = float(getattr(settings, "SOMABRAIN_UTILITY_MU", 0.1) if settings else 0.1)
    nu: float = float(getattr(settings, "SOMABRAIN_UTILITY_NU", 0.05) if settings else 0.05)

    def clamp(
        self,
        lambda_bounds: tuple[float, float] = (
            float(getattr(settings, "utility_lambda_min", 0.0) if settings else 0.0),
            float(getattr(settings, "utility_lambda_max", 5.0) if settings else 5.0),
        ),
        mu_bounds: tuple[float, float] = (
            float(getattr(settings, "utility_mu_min", 0.0) if settings else 0.0),
            float(getattr(settings, "utility_mu_max", 5.0) if settings else 5.0),
        ),
        nu_bounds: tuple[float, float] = (
            float(getattr(settings, "utility_nu_min", 0.0) if settings else 0.0),
            float(getattr(settings, "utility_nu_max", 5.0) if settings else 5.0),
        ),
    ) -> None:
        """Clamp all weights to their respective bounds."""
        self.lambda_ = min(max(self.lambda_, lambda_bounds[0]), lambda_bounds[1])
        self.mu = min(max(self.mu, mu_bounds[0]), mu_bounds[1])
        self.nu = min(max(self.nu, nu_bounds[0]), nu_bounds[1])


@dataclass(frozen=True)
class AdaptationGains:
    """Per-parameter gains applied to the learning signal (settings-driven).

    These gains control how strongly each parameter responds to feedback signals.
    Positive gains increase the parameter on positive feedback, negative gains
    decrease it.

    Attributes:
        alpha: Gain for retrieval alpha parameter
        gamma: Gain for retrieval gamma parameter
        lambda_: Gain for utility lambda parameter
        mu: Gain for utility mu parameter
        nu: Gain for utility nu parameter
    """

    alpha: float = float(
        getattr(settings, "SOMABRAIN_ADAPTATION_GAIN_ALPHA", 1.0) if settings else 1.0
    )
    gamma: float = float(
        getattr(settings, "SOMABRAIN_ADAPTATION_GAIN_GAMMA", -0.5) if settings else -0.5
    )
    lambda_: float = float(
        getattr(settings, "SOMABRAIN_ADAPTATION_GAIN_LAMBDA", 1.0) if settings else 1.0
    )
    mu: float = float(
        getattr(settings, "SOMABRAIN_ADAPTATION_GAIN_MU", -0.25) if settings else -0.25
    )
    nu: float = float(
        getattr(settings, "SOMABRAIN_ADAPTATION_GAIN_NU", -0.25) if settings else -0.25
    )

    @classmethod
    def from_settings(cls) -> "AdaptationGains":
        """Construct gains from centralized settings only."""
        return cls(
            alpha=float(
                getattr(settings, "SOMABRAIN_ADAPTATION_GAIN_ALPHA", 1.0) if settings else 1.0
            ),
            gamma=float(
                getattr(settings, "SOMABRAIN_ADAPTATION_GAIN_GAMMA", -0.5) if settings else -0.5
            ),
            lambda_=float(
                getattr(settings, "SOMABRAIN_ADAPTATION_GAIN_LAMBDA", 1.0) if settings else 1.0
            ),
            mu=float(
                getattr(settings, "SOMABRAIN_ADAPTATION_GAIN_MU", -0.25) if settings else -0.25
            ),
            nu=float(
                getattr(settings, "SOMABRAIN_ADAPTATION_GAIN_NU", -0.25) if settings else -0.25
            ),
        )


@dataclass(frozen=True)
class AdaptationConstraints:
    """Bounds for parameter values during adaptation.

    These constraints prevent parameters from drifting too far from reasonable
    values during online learning.

    Attributes:
        alpha_min/max: Bounds for retrieval alpha
        gamma_min/max: Bounds for retrieval gamma
        lambda_min/max: Bounds for utility lambda
        mu_min/max: Bounds for utility mu
        nu_min/max: Bounds for utility nu
    """

    alpha_min: float = float(
        getattr(settings, "SOMABRAIN_ADAPTATION_ALPHA_MIN", 0.1) if settings else 0.1
    )
    alpha_max: float = float(
        getattr(settings, "SOMABRAIN_ADAPTATION_ALPHA_MAX", 5.0) if settings else 5.0
    )
    gamma_min: float = float(
        getattr(settings, "SOMABRAIN_ADAPTATION_GAMMA_MIN", 0.0) if settings else 0.0
    )
    gamma_max: float = float(
        getattr(settings, "SOMABRAIN_ADAPTATION_GAMMA_MAX", 1.0) if settings else 1.0
    )
    lambda_min: float = float(
        getattr(settings, "SOMABRAIN_ADAPTATION_LAMBDA_MIN", 0.1) if settings else 0.1
    )
    lambda_max: float = float(
        getattr(settings, "SOMABRAIN_ADAPTATION_LAMBDA_MAX", 5.0) if settings else 5.0
    )
    mu_min: float = float(
        getattr(settings, "SOMABRAIN_ADAPTATION_MU_MIN", 0.01) if settings else 0.01
    )
    mu_max: float = float(
        getattr(settings, "SOMABRAIN_ADAPTATION_MU_MAX", 5.0) if settings else 5.0
    )
    nu_min: float = float(
        getattr(settings, "SOMABRAIN_ADAPTATION_NU_MIN", 0.01) if settings else 0.01
    )
    nu_max: float = float(
        getattr(settings, "SOMABRAIN_ADAPTATION_NU_MAX", 5.0) if settings else 5.0
    )

    @classmethod
    def from_settings(cls) -> "AdaptationConstraints":
        """Construct constraints from centralized settings only."""
        return cls(
            alpha_min=float(
                getattr(settings, "SOMABRAIN_ADAPTATION_ALPHA_MIN", 0.1) if settings else 0.1
            ),
            alpha_max=float(
                getattr(settings, "SOMABRAIN_ADAPTATION_ALPHA_MAX", 5.0) if settings else 5.0
            ),
            gamma_min=float(
                getattr(settings, "SOMABRAIN_ADAPTATION_GAMMA_MIN", 0.0) if settings else 0.0
            ),
            gamma_max=float(
                getattr(settings, "SOMABRAIN_ADAPTATION_GAMMA_MAX", 1.0) if settings else 1.0
            ),
            lambda_min=float(
                getattr(settings, "SOMABRAIN_ADAPTATION_LAMBDA_MIN", 0.1) if settings else 0.1
            ),
            lambda_max=float(
                getattr(settings, "SOMABRAIN_ADAPTATION_LAMBDA_MAX", 5.0) if settings else 5.0
            ),
            mu_min=float(
                getattr(settings, "SOMABRAIN_ADAPTATION_MU_MIN", 0.01) if settings else 0.01
            ),
            mu_max=float(
                getattr(settings, "SOMABRAIN_ADAPTATION_MU_MAX", 5.0) if settings else 5.0
            ),
            nu_min=float(
                getattr(settings, "SOMABRAIN_ADAPTATION_NU_MIN", 0.01) if settings else 0.01
            ),
            nu_max=float(
                getattr(settings, "SOMABRAIN_ADAPTATION_NU_MAX", 5.0) if settings else 5.0
            ),
        )