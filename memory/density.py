import numpy as np
from somabrain.metrics.math_metrics import MathematicalMetrics


class DensityMatrix:
    """
    Maintains a PSD density matrix (rho) for second-order memory scoring.
    Supports EMA update, PSD projection, and scoring.
    
    Mathematical Properties:
    - Positive Semi-Definite (PSD)
    - Trace normalization
    - Von Neumann entropy
    - Spectral properties
    """
    
    from somabrain.metrics.advanced_math_metrics import AdvancedMathematicalMetrics

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
            
        # Record initial state metrics
        initial_eigvals = np.linalg.eigvalsh(self.rho)
        self.AdvancedMathematicalMetrics.measure_entropy('initial', initial_eigvals)
        self.AdvancedMathematicalMetrics.measure_state_purity('initial', self.rho)
        
        # Weighted sum of outer products
        delta = sum(w * np.outer(f, f) for f, w in zip(fillers, weights))
        self.rho = (1 - self.lam) * self.rho + self.lam * delta
        
        # Project and normalize
        self.project_psd()
        self.normalize_trace()
        
        # Record final state metrics
        final_eigvals = np.linalg.eigvalsh(self.rho)
        self.AdvancedMathematicalMetrics.measure_entropy('final', final_eigvals)
        self.AdvancedMathematicalMetrics.measure_state_purity('final', self.rho)
        self.AdvancedMathematicalMetrics.measure_spectral_properties(final_eigvals)

    def project_psd(self):
        # Project to PSD by zeroing negative eigenvalues
        eigvals, eigvecs = np.linalg.eigh(self.rho)
        min_eigenval = float(np.min(eigvals))
        MathematicalMetrics.verify_density_matrix(np.trace(self.rho), min_eigenval)
        
        eigvals = np.clip(eigvals, 0, None)
        if np.all(eigvals <= 1e-12):
            floor = 1e-6
            eigvals = np.full_like(eigvals, floor)
        self.rho = (eigvecs * eigvals) @ eigvecs.T
        self.rho = (self.rho + self.rho.T) * 0.5
        
        # Verify mathematical invariant
        MathematicalMetrics.verify_mathematical_invariant('density_matrix_psd', float(self.is_psd()))

    def normalize_trace(self):
        tr = np.trace(self.rho)
        if tr > 0:
            self.rho /= tr
        else:
            self.rho = np.eye(self.d) / self.d
        
        # Verify trace normalization
        MathematicalMetrics.verify_mathematical_invariant('density_matrix_trace', float(abs(np.trace(self.rho) - 1.0)))

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
