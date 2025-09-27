import numpy as np


class DensityMatrix:
    """
    Maintains a PSD density matrix (rho) for second-order memory scoring.
    Supports EMA update, PSD projection, and scoring.
    """

    def __init__(self, d, lam=0.05):
        self.d = d
        self.lam = lam
        self.rho = np.eye(d) / d  # Start as uniform

    def update(self, fillers, weights=None):
        """
        Update rho with new filler vectors (batch outer products, weighted).
        fillers: (N, d) array
        weights: (N,) array or None
        """
        if weights is None:
            weights = np.ones(fillers.shape[0])
        # Weighted sum of outer products
        delta = sum(w * np.outer(f, f) for f, w in zip(fillers, weights))
        self.rho = (1 - self.lam) * self.rho + self.lam * delta
        self.project_psd()
        self.normalize_trace()

    def project_psd(self):
        # Project to PSD by zeroing negative eigenvalues
        eigvals, eigvecs = np.linalg.eigh(self.rho)
        eigvals = np.clip(eigvals, 0, None)
        self.rho = (eigvecs * eigvals) @ eigvecs.T

    def normalize_trace(self):
        tr = np.trace(self.rho)
        if tr > 0:
            self.rho /= tr
        else:
            self.rho = np.eye(self.d) / self.d

    def score(self, hat_f, candidates):
        """
        Score each candidate f_k by s_k = hat_f^T rho f_k
        candidates: (N, d) array
        Returns: (N,) array of scores
        """
        return np.dot(candidates, self.rho @ hat_f)

    def is_psd(self, tol=1e-8):
        eigvals = np.linalg.eigvalsh(self.rho)
        return np.all(eigvals >= -tol)

    def trace(self):
        return np.trace(self.rho)
