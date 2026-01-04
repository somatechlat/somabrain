"""Extended benchmarks for multiple dims and batch sizes."""

import time

import numpy as np

from somabrain import numerics as num


def run(D, N):
    """Execute run.

        Args:
            D: The D.
            N: The N.
        """

    x = np.random.randn(N, D).astype(np.float32)
    t0 = time.time()
    _ = num.normalize_array(x, axis=-1, keepdims=False)
    t1 = time.time()
    t_norm = t1 - t0
    t0 = time.time()
    _ = num.rfft_norm(x, axis=-1)
    t1 = time.time()
    t_rfft = t1 - t0
    return t_norm, t_rfft


if __name__ == "__main__":
    dims = [128, 1024, 2048, 8192]
    Ns = [64, 256, 1024]
    for D in dims:
        for N in Ns:
            tn, tr = run(D, N)
            print(f"D={D} N={N}: normalize {tn:.4f}s, rfft {tr:.4f}s")