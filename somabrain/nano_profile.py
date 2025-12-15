"""
REMOVED: Nano profile configuration for SomaBrain agent kernel.

This module has been removed. All configuration values are now in:
    common.config.settings.Settings

Import directly from Settings:
    from common.config.settings import settings

    # Access values:
    settings.hrr_dim          # was HRR_DIM
    settings.hrr_dtype        # was HRR_DTYPE
    settings.hrr_renorm       # was HRR_RENORM
    settings.hrr_vector_family # was HRR_VECTOR_FAMILY
    settings.bhdc_sparsity    # was BHDC_SPARSITY
    settings.sdr_bits         # was SDR_BITS
    settings.sdr_density      # was SDR_DENSITY
    settings.context_budget_tokens  # was CONTEXT_BUDGET_TOKENS
    settings.max_superpose    # was MAX_SUPERPOSE
    settings.default_wm_slots # was DEFAULT_WM_SLOTS
    settings.global_seed      # was DEFAULT_SEED, SEED
    settings.determinism      # was DETERMINISM
    settings.quota_tenant     # was QUOTAS["tenant"]
    settings.quota_tool       # was QUOTAS["tool"]
    settings.quota_action     # was QUOTAS["action"]
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
