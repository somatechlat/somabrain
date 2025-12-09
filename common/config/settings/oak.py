"""Oak (ROAMDP) settings for SomaBrain.

This module contains configuration for the Oak planning system:
- Option utility calculation
- Planner parameters
- Similarity thresholds
- Reward/novelty thresholds
"""

from __future__ import annotations

from common.config.settings.base import (
    BaseSettings,
    Field,
    _bool_env,
    _float_env,
    _int_env,
)


class OakSettingsMixin(BaseSettings):
    """Oak (ROAMDP) settings mixin."""

    # Feature flag
    ENABLE_OAK: bool = Field(default=_bool_env("ENABLE_OAK", False))

    # Utility calculation
    OAK_BASE_UTILITY: float = Field(default=_float_env("OAK_BASE_UTILITY", 1.0))
    OAK_UTILITY_FACTOR: float = Field(default=_float_env("OAK_UTILITY_FACTOR", 0.1))
    OAK_TAU_MIN: float = Field(default=_float_env("OAK_TAU_MIN", 30.0))
    OAK_TAU_MAX: float = Field(default=_float_env("OAK_TAU_MAX", 300.0))

    # Planner
    OAK_PLAN_MAX_OPTIONS: int = Field(default=_int_env("OAK_PLAN_MAX_OPTIONS", 10))

    # Similarity threshold
    OAK_SIMILARITY_THRESHOLD: float = Field(
        default=_float_env("OAK_SIMILARITY_THRESHOLD", 0.8)
    )

    # Salience / reward thresholds
    OAK_REWARD_THRESHOLD: float = Field(default=_float_env("OAK_REWARD_THRESHOLD", 0.5))
    OAK_NOVELTY_THRESHOLD: float = Field(
        default=_float_env("OAK_NOVELTY_THRESHOLD", 0.2)
    )

    # Discount factor (γ)
    OAK_GAMMA: float = Field(default=_float_env("OAK_GAMMA", 0.99))

    # EMA update factor (α)
    OAK_ALPHA: float = Field(default=_float_env("OAK_ALPHA", 0.1))

    # Kappa weight (κ)
    OAK_KAPPA: float = Field(default=_float_env("OAK_KAPPA", 1.0))
