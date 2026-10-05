"""Graph heat-kernel helpers that wrap the Chebyshev and Lanczos methods.

Provides utilities to apply heat diffusion to a vector on a graph given a
sparse adjacency apply function.
"""

from collections.abc import Callable

import numpy as np

from somabrain.math.lanczos_chebyshev import (
    chebyshev_heat_apply,
    estimate_spectral_interval,
    lanczos_expv,
)

# Safety margin applied to the Lanczos Ritz interval before the Chebyshev
# affine map. Must match the margin used by the production property tests
# (tests/property/test_predictor_properties.py).
SPECTRAL_INTERVAL_EPSILON = 0.1


def expand_spectral_interval(a: float, b: float) -> tuple[float, float]:
    """Expand a Lanczos Ritz interval so it safely contains the spectrum.

    Args:
        a: Estimated lower Ritz bound.
        b: Estimated upper Ritz bound.

    Returns:
        ``(a - ε, b + ε)`` with ``a - ε`` floored at 0 for PSD operators.
    """
    return max(0.0, float(a) - SPECTRAL_INTERVAL_EPSILON), float(b) + SPECTRAL_INTERVAL_EPSILON


def graph_heat_chebyshev(
    apply_A: Callable[[np.ndarray], np.ndarray], x: np.ndarray, t: float, cfg=None
):
    # cfg may provide chebyshev_K or default will be used
    """Execute graph heat chebyshev.

    Args:
        apply_A: The apply_A.
        x: The x.
        t: The t.
        cfg: The cfg.
    """

    K = getattr(cfg, "truth_chebyshev_K", 24) if cfg is not None else 24
    # estimate spectral interval with small lanczos, then expand bounds
    a, b = estimate_spectral_interval(apply_A, n=x.shape[0], m=20)
    a, b = expand_spectral_interval(a, b)
    return chebyshev_heat_apply(apply_A, x, t, K, a, b)


def graph_heat_lanczos(
    apply_A: Callable[[np.ndarray], np.ndarray], x: np.ndarray, t: float, m: int = 32
):
    """Execute graph heat lanczos.

    Args:
        apply_A: The apply_A.
        x: The x.
        t: The t.
        m: The m.
    """

    return lanczos_expv(apply_A, x, t, m=m)
