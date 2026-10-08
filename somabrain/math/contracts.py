"""Single math-contract source for SomaBrain shared constants and formulas.

This module is THE authoritative home for every shared numeric constant and
closed-form math helper used across learning, annealing, scoring, working
memory, settings, and the BHDC encoder. One concept = one definition.

Consumers MUST import from this module rather than re-declaring values.

Scope (per SOMA-BR-PLAN-MASTER-001 Wave W1):
    - ADAPT_GAINS / ADAPT_BOUNDS: signed adaptation gains and clamp bounds
    - TAU_FLOOR / TAU_DECAY_FACTOR / TAU_INTERVAL: single tau schedule set
    - RECENCY_*: canonical stretched-exponential recency kernel parameters
    - SCORER_WEIGHTS / SCORER_WEIGHT_MIN / SCORER_WEIGHT_MAX
    - PROMOTE_THETA / PROMOTE_TICKS: WM→LTM promotion contract
    - NEURO_BOUNDS: neuromodulator clamp table
    - BHDC_D / BHDC_P / QUANT_STEP: hypervector dimension, sparsity, quant step
    - Wiener ridge λ* helpers (GMD Theorem 3) — single home (moved from
      ``bhdc_encoder``; ``bhdc_encoder`` imports from here).
"""

from __future__ import annotations

import math
import os
from collections.abc import Sequence
from typing import Final

# ---------------------------------------------------------------------------
# BHDC / quantization constants
# ---------------------------------------------------------------------------

#: Hypervector dimension D (matches ``SOMABRAIN_HRR_DIM`` / brain_settings
#: ``hrr_dim`` default).  Engineering choice — not a theorem-derived optimum.
BHDC_D: Final[int] = 8192

#: Active-dimension fraction p for sparse hypervectors.  Engineering choice,
#: not the output of a sparsity theorem (see MATH-TRUTH T12).  Matches
#: ``SOMABRAIN_BHDC_SPARSITY`` default.
BHDC_P: Final[float] = 0.1

#: Alias kept for Wiener / encoder call sites that expect the historical name.
PRODUCTION_SPARSITY_P: Final[float] = BHDC_P

#: Quantization step Δ on [-1, 1] at 8-bit: ``2 / (2^8 − 1) = 2/255``.
QUANT_STEP: Final[float] = 2.0 / 255.0

#: Quantization bits honoured by the Wiener formula and the 8-bit quantizer.
QUANT_BITS: Final[int] = 8


# ---------------------------------------------------------------------------
# Wiener ridge λ* (GMD Theorem 3) — single home
# ---------------------------------------------------------------------------


def compute_wiener_lambda(p: float, bits: int = QUANT_BITS) -> float:
    """Wiener ridge λ* = σ_ε² / σ_v² (GMD Theorem 3).

    σ_ε² = Δ²/12 with Δ = 2/(2^bits − 1) (Δ = 2/255 for the 8-bit quantizer),
    σ_v² = p(1−p) for a sparse vector with active probability p.
    At bits=8 this is exactly ``Δ² / (12 p (1−p))``.

    Matches ``somabrain_rs.compute_wiener_lambda``.
    """
    p_clamped = min(max(float(p), 0.01), 0.99)
    bits_clamped = max(int(bits), 1)
    levels = float((1 << bits_clamped) - 1)
    delta = 2.0 / levels
    sigma_eps_sq = (delta * delta) / 12.0
    sigma_v_sq = p_clamped * (1.0 - p_clamped)
    return sigma_eps_sq / sigma_v_sq


def production_sparsity() -> float:
    """BHDC active probability p used in production.

    Reads ``SOMABRAIN_BHDC_SPARSITY`` — the same environment variable (and
    default) as ``somabrain.settings.cognitive.SOMABRAIN_BHDC_SPARSITY``.
    """
    return float(os.environ.get("SOMABRAIN_BHDC_SPARSITY", BHDC_P))


def production_wiener_lambda(bits: int = QUANT_BITS) -> float:
    """λ* evaluated at the production sparsity."""
    return compute_wiener_lambda(production_sparsity(), bits)


# ---------------------------------------------------------------------------
# Adaptation gains (signed, Python contract — γ negative)
# ---------------------------------------------------------------------------
# DEBT-008: Python and Rust must share these signs and magnitudes.
# The values below are the single source; ``learning/config.py`` and
# ``settings/cognitive.py`` read from here.

#: Per-parameter gains: positive gain increases the parameter on positive
#: feedback, negative gain decreases it.  γ/μ/ν are negative by design so
#: retrieval-temporal and utility secondary/tertiary weights fall on reward.
ADAPT_GAINS: Final[dict[str, float]] = {
    "alpha": 1.0,
    "gamma": -0.5,
    "lambda_": 1.0,
    "mu": -0.25,
    "nu": -0.25,
}

#: Clamp bounds for the five adapted parameters.
ADAPT_BOUNDS: Final[dict[str, tuple[float, float]]] = {
    "alpha": (0.1, 5.0),
    "gamma": (0.0, 1.0),
    "lambda_": (0.1, 5.0),
    "mu": (0.01, 5.0),
    "nu": (0.01, 5.0),
}

# ---------------------------------------------------------------------------
# Tau schedule — ONE set (from the live runtime task tasks/temperature_anneal.py)
# ---------------------------------------------------------------------------
# DEF-05 / DEF-06 / DEBT-009: previously four floors and two decay semantics.
# These three constants are the only tau schedule values.

#: Lower bound for the retrieval temperature τ.
TAU_FLOOR: Final[float] = 0.1

#: Multiplicative decay factor applied per anneal interval (τ ← τ · factor).
TAU_DECAY_FACTOR: Final[float] = 0.95

#: Anneal interval in seconds for the background temperature-anneal task.
TAU_INTERVAL: Final[float] = 60.0


def anneal_tau(
    tau: float,
    factor: float = TAU_DECAY_FACTOR,
    floor: float = TAU_FLOOR,
) -> float:
    """The ONE tau anneal law (geometric).

    ``τ ← max(floor, τ · factor)``

    Live schedule (``tasks/temperature_anneal.py``): applied once per
    ``TAU_INTERVAL`` seconds. Rust mirror: ``somabrain_rs.anneal_tau`` —
    same formula, same meaning. There is no linear/exponential/step variant.
    """
    return max(float(floor), float(tau) * float(factor))


def entropy_of(weights: Sequence[float]) -> float:
    """Shannon entropy of a linear-normalised weight vector (natural log).

    ``p_i = w_i / Σ w``; ``H = −Σ p_i · ln p_i`` for ``p_i > 0``.
    """
    vals = [max(0.0, float(w)) for w in weights]
    total = sum(vals)
    if total <= 0.0:
        return 0.0
    return -sum((v / total) * math.log(v / total) for v in vals if v > 0.0)


def sharpen_mixture_weights(
    weights: Sequence[float],
    cap: float,
    sharpen_rate: float = 0.8,
    final_sharpen: float = 0.05,
    max_iters: int = 10,
) -> tuple[list[float], bool]:
    """ONE mass rule for entropy-cap sharpening of mixture weights.

    Operates on a mixture-weight vector (α, β, γ) — **never** on τ.  τ is a
    temperature, not a mass; callers must not pass it in (DEBT-010).

    If ``H(w) ≤ cap`` the vector is returned unchanged.  Otherwise
    non-dominant components are scaled by ``sharpen_rate`` (up to
    ``max_iters`` times) and finally by ``final_sharpen``.  The mass of the
    dominant component is preserved in absolute terms; the remaining mass is
    redistributed to keep the vector's total mass unchanged.

    Returns ``(new_weights, was_sharpened)``.
    """
    vec = [max(1e-9, float(w)) for w in weights]
    if not vec:
        return [], False
    cap = float(cap)
    if cap <= 0.0:
        return list(vec), False

    original_sum = sum(vec)
    if original_sum <= 0.0:
        return list(vec), False

    h = entropy_of(vec)
    if h <= cap:
        return list(vec), False

    largest_idx = max(range(len(vec)), key=lambda i: vec[i])
    for _ in range(max(0, int(max_iters))):
        for i in range(len(vec)):
            if i != largest_idx:
                vec[i] *= float(sharpen_rate)
        h = entropy_of(vec)
        if h <= cap:
            break
    if h > cap:
        for i in range(len(vec)):
            if i != largest_idx:
                vec[i] *= float(final_sharpen)
        h = entropy_of(vec)

    # Restore original total mass (dominant keeps its share of the mass rule).
    new_sum = sum(vec)
    if new_sum > 0.0:
        scale = original_sum / new_sum
        vec = [v * scale for v in vec]
    return vec, True

# ---------------------------------------------------------------------------
# Recency kernel parameters (stretched exponential)
# ---------------------------------------------------------------------------
# R(age) = clamp(exp(-(age/scale)^sharpness), floor, 1)
# Scale is the ONE recency time scale for every call site.

#: Recency time scale in seconds.
RECENCY_SCALE: Final[float] = 60.0

#: Stretch exponent for the recency kernel.
RECENCY_SHARPNESS: Final[float] = 1.2

#: Lower clamp for the recency boost.
RECENCY_FLOOR: Final[float] = 0.05

#: Cap for the monotone step feature ``log1p(age/scale)*sharpness``.
RECENCY_CAP: Final[float] = 1000.0

# ---------------------------------------------------------------------------
# Unified scorer weights
# ---------------------------------------------------------------------------
# score = clamp( w_cosine·cos + w_fd·fd + w_recency·rec , 0, 1 )
# Renormalised over active components so the ceiling is always 1.0.

#: (cosine, fd, recency) default weight triple.
SCORER_WEIGHTS: Final[tuple[float, float, float]] = (0.6, 0.25, 0.15)

#: Per-component clamp bounds for scorer weights.
SCORER_WEIGHT_MIN: Final[float] = 0.0
SCORER_WEIGHT_MAX: Final[float] = 1.0

# ---------------------------------------------------------------------------
# WM→LTM promotion contract
# ---------------------------------------------------------------------------

#: Salience threshold for promotion eligibility.
PROMOTE_THETA: Final[float] = 0.85

#: Consecutive ticks above threshold required before promotion.
PROMOTE_TICKS: Final[int] = 3

# ---------------------------------------------------------------------------
# Lexical ranking bonus contract (one formula, one home)
# ---------------------------------------------------------------------------
#: Exact field match bonus.
LEXICAL_BONUS_EXACT: Final[float] = 1.5
#: Query-as-substring field match bonus.
LEXICAL_BONUS_SUBSTRING: Final[float] = 1.0
#: Per-token overlap weight.
LEXICAL_BONUS_TOKEN: Final[float] = 0.25
#: Cap on the token-overlap term.
LEXICAL_BONUS_TOKEN_CAP: Final[float] = 1.0

# ---------------------------------------------------------------------------
# Outbox backpressure (E2.5)
# ---------------------------------------------------------------------------
#: Pending-outbox count that engages backpressure.
OUTBOX_BACKPRESSURE_THRESHOLD: Final[int] = 10000

# ---------------------------------------------------------------------------
# Adaptation / learning-rate schedule (one home)
# ---------------------------------------------------------------------------
#: DA→LR scale floor (scale = clamp(floor + dopamine, floor, ceil)).
ADAPT_LR_SCALE_FLOOR: Final[float] = 0.5
#: DA→LR scale ceiling.
ADAPT_LR_SCALE_CEIL: Final[float] = 1.2
#: Curriculum "easy" LR multiplier.
ADAPT_STAGE_EASY: Final[float] = 1.2
#: Curriculum "hard" LR multiplier.
ADAPT_STAGE_HARD: Final[float] = 0.5
#: Tau error-damping coefficient (τ ← τ · (1 − coef·error)).
TAU_ERROR_COEF: Final[float] = 0.05

# ---------------------------------------------------------------------------
# Predictor EWMA (Mahalanobis online mean/var)
# ---------------------------------------------------------------------------
#: EWMA learning rate for the Mahalanobis predictor.
PREDICTOR_EWMA_ALPHA: Final[float] = 0.01

# ---------------------------------------------------------------------------
# Neuromodulator bounds
# ---------------------------------------------------------------------------
# One clamp table for every consumer (API, Rust ODE, Python hubs).
# Keys: dopamine, serotonin, noradrenaline, acetylcholine.

NEURO_BOUNDS: Final[dict[str, tuple[float, float]]] = {
    "dopamine": (0.2, 0.8),
    "serotonin": (0.0, 1.0),
    "noradrenaline": (0.0, 0.1),
    "acetylcholine": (0.0, 0.1),
}

# ---------------------------------------------------------------------------
# Numerical floors used on math paths
# ---------------------------------------------------------------------------

#: Canonical numerical epsilon for Python math modules (normalize, similarity).
MATH_EPS: Final[float] = 1e-12

#: Reciprocal-tau guard used in softmax weight computation.
TAU_RECIPROCAL_FLOOR: Final[float] = 1e-6

# ---------------------------------------------------------------------------
# Re-exports for the documented single-import surface
# ---------------------------------------------------------------------------
# These names are defined above; listed here for ``__all__`` completeness.

__all__ = [
    # BHDC / quantization
    "BHDC_D",
    "BHDC_P",
    "PRODUCTION_SPARSITY_P",
    "QUANT_STEP",
    "QUANT_BITS",
    # Wiener λ*
    "compute_wiener_lambda",
    "production_sparsity",
    "production_wiener_lambda",
    # Adaptation
    "ADAPT_GAINS",
    "ADAPT_BOUNDS",
    # Tau schedule
    "TAU_FLOOR",
    "TAU_DECAY_FACTOR",
    "TAU_INTERVAL",
    "anneal_tau",
    # Entropy / mass rule
    "entropy_of",
    "sharpen_mixture_weights",
    # Recency
    "RECENCY_SCALE",
    "RECENCY_SHARPNESS",
    "RECENCY_FLOOR",
    "RECENCY_CAP",
    # Scorer
    "SCORER_WEIGHTS",
    "SCORER_WEIGHT_MIN",
    "SCORER_WEIGHT_MAX",
    # Promotion
    "PROMOTE_THETA",
    "PROMOTE_TICKS",
    # Lexical bonus
    "LEXICAL_BONUS_EXACT",
    "LEXICAL_BONUS_SUBSTRING",
    "LEXICAL_BONUS_TOKEN",
    "LEXICAL_BONUS_TOKEN_CAP",
    # Outbox
    "OUTBOX_BACKPRESSURE_THRESHOLD",
    # Adaptation / LR
    "ADAPT_LR_SCALE_FLOOR",
    "ADAPT_LR_SCALE_CEIL",
    "ADAPT_STAGE_EASY",
    "ADAPT_STAGE_HARD",
    "TAU_ERROR_COEF",
    # Predictor
    "PREDICTOR_EWMA_ALPHA",
    # Neuromod
    "NEURO_BOUNDS",
    # Numerics
    "MATH_EPS",
    "TAU_RECIPROCAL_FLOOR",
]
