"""Core math utilities for the BHDC-era SomaBrain."""

from .bhdc_encoder import BHDCEncoder, PermutationBinder
from .fd_rho import FrequentDirections
from .lanczos_chebyshev import chebyshev_heat_apply, estimate_spectral_interval
from common.logging import logger

__all__ = [
    "BHDCEncoder",
    "PermutationBinder",
    "FrequentDirections",
    "chebyshev_heat_apply",
    "estimate_spectral_interval",
]
