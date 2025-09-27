"""Experimental math utilities for somabrain.

This package contains compact, well-documented implementations used for
experiments: learned unitary roles for HRR, a Frequent-Directions (FD)
covariance sketch, and a Lanczos+Chebyshev helper for heat-kernel
approximation. These are intentionally lightweight and self-contained so
they can be reviewed and iterated on quickly.
"""

from .learned_roles import LearnedUnitaryRoles, bind_fft, unbind_fft
from .fd_rho import FrequentDirections
from .lanczos_chebyshev import chebyshev_heat_apply, estimate_spectral_interval

__all__ = [
    "LearnedUnitaryRoles",
    "bind_fft",
    "unbind_fft",
    "FrequentDirections",
    "chebyshev_heat_apply",
    "estimate_spectral_interval",
]
