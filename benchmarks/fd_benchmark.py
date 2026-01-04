"""Micro-benchmark for Frequent-Directions sketch accuracy.

Run from the repo root with the project's venv:
    python benchmarks/fd_benchmark.py
"""

import numpy as np
from somabrain.math.fd_rho import sketch_from_matrix, topk_eigenvalues_from_sketch


def main():
    """Execute main.
        """

    rng = np.random.default_rng(42)
    n = 2000
    d = 128
    r0 = 8
    A = rng.normal(size=(n, r0))
    B = rng.normal(size=(r0, d))
    X = A @ B

    C = X.T @ X
    true_vals = np.linalg.svd(C, compute_uv=False)

    for ell in (2 * r0, 4 * r0, 8 * r0):
        fd = sketch_from_matrix(X, ell=ell)
        approx_vals = topk_eigenvalues_from_sketch(fd, k=r0)
        rel_err = np.linalg.norm(true_vals[:r0] - approx_vals[:r0]) / (
            np.linalg.norm(true_vals[:r0]) + 1e-12
        )
        print(f"ell={ell} rel_err_top{r0}={rel_err:.4f}")


if __name__ == "__main__":
    main()