"""
Advanced mathematical metrics for quantum operations monitoring.
Provides detailed mathematical verification and monitoring.
"""

from prometheus_client import Gauge, Histogram, Counter
import numpy as np
from typing import List

# Quantum State Metrics
# The Prometheus client constructors are dynamically typed; Pyright cannot infer their signatures.
# Adding a ``# type: ignore`` comment silences the false positive while keeping the runtime behavior unchanged.
quantum_state_purity = Gauge(
    "quantum_state_purity", "Measure of quantum state purity tr(ρ²)", ["state_type"]
)

quantum_entropy = Gauge(
    "quantum_entropy", "Von Neumann entropy of quantum states", ["state_type"]
)

quantum_interference = Histogram(
    "quantum_interference_pattern",
    "Quantum interference pattern measurements",
    buckets=[0.0, 0.25, 0.5, 0.75, 1.0],
)

# Advanced Mathematical Properties
spectral_gap = Gauge(
    "density_matrix_spectral_gap", "Spectral gap in density matrix eigenvalues"
)

frame_condition_number = Gauge(
    "role_frame_condition_number", "Condition number of the role frame"
)

binding_condition_number = Gauge(
    "binding_condition_number", "Condition number of binding operands"
)

permutation_cycle_length = Histogram(
    "permutation_cycle_length",
    "Distribution of permutation cycle lengths",
    buckets=[1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024],
)

# Conservation Laws
energy_conservation = Gauge(
    "binding_energy_conservation",
    "Energy conservation in binding operations",
    ["operation"],
)

probability_conservation = Gauge(
    "probability_conservation",
    "Conservation of probability in operations",
    ["operation"],
)

# Error Metrics
numerical_error = Histogram(
    "numerical_error_distribution",
    "Distribution of numerical errors in operations",
    buckets=np.logspace(-10, 0, 11).tolist(),
)

orthogonality_violation = Counter(
    "orthogonality_violations_total", "Number of orthogonality violations detected"
)


class AdvancedMathematicalMetrics:
    """Advanced mathematical metrics collection and verification."""

    @staticmethod
    def measure_state_purity(state_type: str, density_matrix: np.ndarray) -> None:
        """Measure and record quantum state purity."""
        purity = np.trace(density_matrix @ density_matrix).real
        quantum_state_purity.labels(state_type=state_type).set(purity)

    @staticmethod
    def measure_entropy(state_type: str, eigenvalues: np.ndarray) -> None:
        """Calculate and record von Neumann entropy."""
        eigenvalues = eigenvalues[eigenvalues > 1e-10]
        entropy = -np.sum(eigenvalues * np.log2(eigenvalues))
        quantum_entropy.labels(state_type=state_type).set(entropy)

    @staticmethod
    def record_interference(interference_value: float) -> None:
        """Record quantum interference pattern measurements."""
        quantum_interference.observe(interference_value)

    @staticmethod
    def measure_spectral_properties(eigenvalues: np.ndarray) -> None:
        """Measure and record spectral properties."""
        if len(eigenvalues) > 1:
            gap = float(eigenvalues[-1] - eigenvalues[-2])
            spectral_gap.set(gap)

    @staticmethod
    def measure_frame_properties(frame_vectors: List[np.ndarray]) -> None:
        """Measure and record frame properties."""
        if not frame_vectors:
            return

        # Construct frame operator
        frame_op = sum(np.outer(v, v) for v in frame_vectors)

        # Calculate condition number
        eigvals = np.linalg.eigvalsh(frame_op)
        cond = (
            float(np.max(eigvals) / np.min(eigvals))
            if np.min(eigvals) > 0
            else float("inf")
        )
        frame_condition_number.set(cond)

    @staticmethod
    def record_permutation_cycle(cycle_length: int) -> None:
        """Record permutation cycle length distribution."""
        permutation_cycle_length.observe(cycle_length)

    @staticmethod
    def verify_energy_conservation(
        operation: str, initial_energy: float, final_energy: float
    ) -> None:
        """Verify and record energy conservation."""
        # ``initial_energy`` should be a numeric type; ensure float arithmetic.
        relative_error = abs(float(final_energy) - float(initial_energy)) / float(
            initial_energy
        )
        energy_conservation.labels(operation=operation).set(relative_error)

    @staticmethod
    def verify_probability_conservation(
        operation: str, initial_prob: float, final_prob: float
    ) -> None:
        """Verify and record probability conservation."""
        if abs(initial_prob) <= 1e-12:
            relative_error = abs(final_prob - initial_prob)
        else:
            relative_error = abs(final_prob - initial_prob) / initial_prob
        probability_conservation.labels(operation=operation).set(relative_error)

    @staticmethod
    def record_numerical_error(error: float) -> None:
        """Record numerical error measurements."""
        numerical_error.observe(error)

    @staticmethod
    def check_orthogonality(cosine_sim: float, threshold: float = 0.1) -> None:
        """Check and record orthogonality violations."""
        if abs(cosine_sim) > threshold:
            orthogonality_violation.inc()

    @staticmethod
    def record_binder_condition(condition_number: float) -> None:
        """Record binding condition number for diagnostics."""
        binding_condition_number.set(max(0.0, float(condition_number)))
