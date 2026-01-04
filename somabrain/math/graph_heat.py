"""Graph heat-kernel helpers that wrap the Chebyshev and Lanczos methods.

Provides utilities to apply heat diffusion to a vector on a graph given a
sparse adjacency apply function.
"""

from typing import Callable
import numpy as np
from somabrain.math.lanczos_chebyshev import (
    estimate_spectral_interval,
    chebyshev_heat_apply,
    lanczos_expv,
)


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
    # estimate spectral interval with small lanczos
    a, b = estimate_spectral_interval(apply_A, n=x.shape[0], m=20)
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