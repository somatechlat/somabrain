import numpy as np
from somabrain.math.fd_rho import sketch_from_matrix, topk_eigenvalues_from_sketch


def test_fd_sketch_topk_accuracy():
    # create a low-rank matrix X (n x d) with rank r0
    n = 500
    d = 64
    r0 = 5
    rng = np.random.default_rng(1)
    A = rng.normal(size=(n, r0))
    B = rng.normal(size=(r0, d))
    X = A @ B  # rank r0

    # true covariance top eigenvalues
    C = X.T @ X
    true_vals = np.linalg.svd(C, compute_uv=False)
    k = r0

    # sketch size small but > k
    ell = 2 * k + 2
    fd = sketch_from_matrix(X, ell=ell)
    approx_vals = topk_eigenvalues_from_sketch(fd, k=k)

    # compute relative error on top-k eigenvalues
    rel_err = np.linalg.norm(true_vals[:k] - approx_vals[:k]) / (
        np.linalg.norm(true_vals[:k]) + 1e-12
    )
    assert (
        rel_err < 0.5
    )  # FD is approximate; expect relative error < 50% for this setting
