"""Core math utilities for the BHDC-era SomaBrain.

This module provides canonical implementations of mathematical operations
used throughout the SomaBrain system. All similarity and normalization
operations MUST use the functions exported from this module.

CANONICAL IMPLEMENTATIONS (SINGLE SOURCE OF TRUTH):
    - cosine_similarity: Vector similarity computation
    - normalize_vector: L2 normalization
    - normalize_batch: Batch L2 normalization
"""

from .bhdc_encoder import (
    BHDCEncoder,
    PermutationBinder,
    compute_wiener_lambda,
    fwht,
    production_sparsity,
    production_wiener_lambda,
)
from .fd_rho import FrequentDirections
from .lanczos_chebyshev import chebyshev_heat_apply, estimate_spectral_interval
from .normalize import (
    ensure_unit_norm,
    normalize_batch,
    normalize_vector,
    safe_normalize,
)
from .recency import (
    recency_features,
    recency_steps,
    stretched_exponential_recency,
)
from .similarity import (
    batch_cosine_similarity,
    cosine_distance,
    cosine_error,
    cosine_similarity,
)

__all__ = [
    # Canonical similarity functions
    "cosine_similarity",
    "cosine_error",
    "cosine_distance",
    "batch_cosine_similarity",
    # Canonical normalization functions
    "normalize_vector",
    "safe_normalize",
    "normalize_batch",
    "ensure_unit_norm",
    # BHDC encoder
    "BHDCEncoder",
    "PermutationBinder",
    # Wiener ridge λ* (GMD Theorem 3) and FWHT (GMD Theorem 4)
    "compute_wiener_lambda",
    "production_wiener_lambda",
    "production_sparsity",
    "fwht",
    # Frequent Directions
    "FrequentDirections",
    # Spectral methods
    "chebyshev_heat_apply",
    "estimate_spectral_interval",
    # Recency kernel (single family)
    "stretched_exponential_recency",
    "recency_steps",
    "recency_features",
]
