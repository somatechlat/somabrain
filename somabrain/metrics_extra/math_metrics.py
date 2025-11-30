from prometheus_client import Gauge, Histogram
import numpy as np

"""
Mathematical metrics for monitoring quantum operations and invariants.
Pure mathematical verification, no approximations.
"""


# Quantum Operation Metrics
quantum_spectral_property = Gauge(
    "quantum_hrr_spectral_property", "Verify |H_k|≈1 for all operations", ["operation"]
)

quantum_binding_accuracy = Histogram(
    "quantum_binding_accuracy",
    "Measure binding/unbinding roundtrip accuracy",
    buckets=[0.9, 0.95, 0.99, 0.995, 0.999, 1.0], )

quantum_role_orthogonality = Gauge(
    "quantum_role_orthogonality", "Verify role vector orthogonality", ["role_pair"]
)

# Density Matrix Metrics
density_matrix_trace = Gauge("density_matrix_trace", "Verify |tr(ρ) - 1| < 1e-4")

density_matrix_min_eigenvalue = Gauge(
    "density_matrix_min_eigenvalue",
    "Minimum eigenvalue of density matrix (should be ≥ 0)", )

# Implementation Verification Metrics
mathematical_invariant = Gauge(
    "mathematical_invariant_verified",
    "Track mathematical invariant verification",
    ["invariant"], )

operation_correctness = Gauge(
    "operation_mathematical_correctness", "Verify operation correctness", ["operation"]
)


class MathematicalMetrics:
    """Collector for mathematical verification metrics."""

@staticmethod
def verify_spectral_property(operation: str, magnitudes: np.ndarray) -> None:
        """Verify and record spectral property |H_k|≈1."""
        deviation = np.abs(np.mean(magnitudes) - 1.0)
        quantum_spectral_property.labels(operation=operation).set(1.0 - deviation)

@staticmethod
def record_binding_accuracy(accuracy: float) -> None:
        """Record binding/unbinding roundtrip accuracy."""
        quantum_binding_accuracy.observe(accuracy)

@staticmethod
def verify_role_orthogonality(role1: str, role2: str, cosine_sim: float) -> None:
        """Verify and record role vector orthogonality."""
        quantum_role_orthogonality.labels(role_pair=f"{role1}:{role2}").set(
            abs(cosine_sim)
        )

@staticmethod
def verify_density_matrix(trace_value: float, min_eigenval: float) -> None:
        """Verify and record density matrix properties."""
        density_matrix_trace.set(abs(trace_value - 1.0))
        density_matrix_min_eigenvalue.set(min_eigenval)

@staticmethod
def verify_mathematical_invariant(invariant: str, value: float) -> None:
        """Record mathematical invariant verification."""
        mathematical_invariant.labels(invariant=invariant).set(value)

@staticmethod
def verify_operation_correctness(operation: str, value: float) -> None:
        """Record operation correctness verification."""
        operation_correctness.labels(operation=operation).set(value)
