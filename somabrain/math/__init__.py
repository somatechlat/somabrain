"""Core math utilities for the BHDC-era SomaBrain.

This module provides canonical implementations of mathematical operations
used throughout the SomaBrain system. All similarity and normalization
operations MUST use the functions exported from this module.

CANONICAL IMPLEMENTATIONS (SINGLE SOURCE OF TRUTH):
    - cosine_similarity: Vector similarity computation
    - normalize_vector: L2 normalization
    - normalize_batch: Batch L2 normalization

Shared constants and the Wiener λ* formula live in ``somabrain.math.contracts``.
"""

from .bhdc_encoder import (
    BHDCEncoder,
    PermutationBinder,
    fwht,
)
from .contracts import (
    ADAPT_BOUNDS,
    ADAPT_GAINS,
    BHDC_D,
    BHDC_P,
    MATH_EPS,
    NEURO_BOUNDS,
    PROMOTE_THETA,
    PROMOTE_TICKS,
    QUANT_STEP,
    RECENCY_CAP,
    RECENCY_FLOOR,
    RECENCY_SCALE,
    RECENCY_SHARPNESS,
    SCORER_WEIGHT_MAX,
    SCORER_WEIGHT_MIN,
    SCORER_WEIGHTS,
    TAU_DECAY_FACTOR,
    TAU_FLOOR,
    TAU_INTERVAL,
    compute_wiener_lambda,
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
    # Shared math contracts (single source)
    "ADAPT_GAINS",
    "ADAPT_BOUNDS",
    "BHDC_D",
    "BHDC_P",
    "MATH_EPS",
    "NEURO_BOUNDS",
    "PROMOTE_THETA",
    "PROMOTE_TICKS",
    "QUANT_STEP",
    "RECENCY_CAP",
    "RECENCY_FLOOR",
    "RECENCY_SCALE",
    "RECENCY_SHARPNESS",
    "SCORER_WEIGHTS",
    "SCORER_WEIGHT_MIN",
    "SCORER_WEIGHT_MAX",
    "TAU_DECAY_FACTOR",
    "TAU_FLOOR",
    "TAU_INTERVAL",
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
