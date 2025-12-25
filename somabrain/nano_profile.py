"""
REMOVED: Nano profile configuration for SomaBrain agent kernel.

This module has been removed. All configuration values are now in:
    common.config.settings.Settings

Import directly from Settings:
    from django.conf import settings

    # Access values:
    settings.SOMABRAIN_HRR_DIM          # was HRR_DIM
    settings.SOMABRAIN_HRR_DTYPE        # was HRR_DTYPE
    settings.SOMABRAIN_HRR_RENORM       # was HRR_RENORM
    settings.SOMABRAIN_HRR_VECTOR_FAMILY # was HRR_VECTOR_FAMILY
    settings.SOMABRAIN_BHDC_SPARSITY    # was BHDC_SPARSITY
    settings.SOMABRAIN_SDR_BITS         # was SDR_BITS
    settings.SOMABRAIN_SDR_DENSITY      # was SDR_DENSITY
    settings.SOMABRAIN_CONTEXT_BUDGET_TOKENS  # was CONTEXT_BUDGET_TOKENS
    settings.SOMABRAIN_MAX_SUPERPOSE    # was MAX_SUPERPOSE
    settings.SOMABRAIN_DEFAULT_WM_SLOTS # was DEFAULT_WM_SLOTS
    settings.SOMABRAIN_GLOBAL_SEED      # was DEFAULT_SEED, SEED
    settings.SOMABRAIN_DETERMINISM      # was DETERMINISM
    settings.SOMABRAIN_QUOTA_TENANT     # was QUOTAS["tenant"]
    settings.SOMABRAIN_QUOTA_TOOL       # was QUOTAS["tool"]
    settings.SOMABRAIN_QUOTA_ACTION     # was QUOTAS["action"]
"""

from __future__ import annotations


class _RemovedConstant:
    """Sentinel that raises error on any access to removed constants."""

    def __init__(self, name: str):
        self._name = name

    def __repr__(self) -> str:
        raise AttributeError(self._error_msg())

    def __str__(self) -> str:
        raise AttributeError(self._error_msg())

    def __bool__(self) -> bool:
        raise AttributeError(self._error_msg())

    def __int__(self) -> int:
        raise AttributeError(self._error_msg())

    def __float__(self) -> float:
        raise AttributeError(self._error_msg())

    def __getitem__(self, key):
        raise AttributeError(self._error_msg())

    def _error_msg(self) -> str:
        return (
            f"somabrain.nano_profile.{self._name} has been removed. "
            f"Use common.config.settings.settings instead."
        )


# All constants removed - accessing them raises clear error
HRR_DIM = _RemovedConstant("HRR_DIM")
HRR_DTYPE = _RemovedConstant("HRR_DTYPE")
HRR_RENORM = _RemovedConstant("HRR_RENORM")
HRR_VECTOR_FAMILY = _RemovedConstant("HRR_VECTOR_FAMILY")
BHDC_SPARSITY = _RemovedConstant("BHDC_SPARSITY")
SDR_BITS = _RemovedConstant("SDR_BITS")
SDR_DENSITY = _RemovedConstant("SDR_DENSITY")
CONTEXT_BUDGET_TOKENS = _RemovedConstant("CONTEXT_BUDGET_TOKENS")
MAX_SUPERPOSE = _RemovedConstant("MAX_SUPERPOSE")
DEFAULT_WM_SLOTS = _RemovedConstant("DEFAULT_WM_SLOTS")
DEFAULT_SEED = _RemovedConstant("DEFAULT_SEED")
SEED = _RemovedConstant("SEED")
DETERMINISM = _RemovedConstant("DETERMINISM")
QUOTAS = _RemovedConstant("QUOTAS")
