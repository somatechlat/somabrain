"""Targeted spectral nulling test to exercise unbind fragility.

Run under the project's venv with PYTHONPATH=. to validate imports and API.
"""

import numpy as np

from somabrain.math import cosine_similarity
from somabrain.numerics import irfft_norm, rfft_norm
from somabrain.quantum import HRRConfig, QuantumLayer


def run_once(seed: int = 1234, D: int = 1024, null_frac: float = 0.2):
    """Execute run once.

        Args:
            seed: The seed.
            D: The D.
            null_frac: The null_frac.
        """

    rng = np.random.default_rng(seed)
    cfg = HRRConfig(dim=D)
    q = QuantumLayer(cfg)

    # QuantumLayer.random_vector() uses the layer's internal RNG seeded by
    # HRRConfig.seed; do not pass an external rng. We use rng below for the
    # spectral nulling selection only to keep the test reproducible.
    a = q.random_vector()
    b = q.random_vector()

    fb = rfft_norm(b, n=D)
    n_null = int(null_frac * fb.shape[-1])
    idx = rng.choice(fb.shape[-1], size=n_null, replace=False)
    fb[idx] = 0.0
    b_null = irfft_norm(fb, n=D)

    bound = q.bind(a, b_null)
    est_exact = q.unbind_exact(bound, b_null)
    est_robust = q.unbind(bound, b_null)
    est_wiener = q.unbind_wiener(bound, b_null)

    print("cosine_exact", cosine_similarity(a, est_exact))
    print("cosine_robust", cosine_similarity(a, est_robust))
    print("cosine_wiener", cosine_similarity(a, est_wiener))


if __name__ == "__main__":
    run_once()