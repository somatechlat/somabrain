"""
Tests for verifying mathematical properties of HRR operations.
No mocks, no approximations - pure mathematical verification.
"""

import numpy as np
import pytest
from numpy.testing import assert_allclose

from somabrain.quantum import HRRConfig, QuantumLayer
from memory.density import DensityMatrix


@pytest.fixture
def quantum_layer():
    """Create a quantum layer with standard test dimensions."""
    cfg = HRRConfig(dim=8192, seed=42, sparsity=0.1)
    return QuantumLayer(cfg)


def test_role_unitary_properties(quantum_layer):
    """Verify that role vectors maintain unitary properties |H_k|≈1."""
    role = quantum_layer.make_unitary_role("test::role")

    # Verify unit norm
    norm = np.linalg.norm(role)
    assert_allclose(norm, 1.0, rtol=1e-5)

    # Verify spectral properties (Parseval's theorem)
    fft_role = np.fft.fft(role)
    sum_sq_time = np.sum(role**2)
    sum_sq_freq = np.sum(np.abs(fft_role) ** 2) / quantum_layer.cfg.dim
    assert_allclose(sum_sq_time, sum_sq_freq, rtol=1e-5)


def test_binding_invertibility(quantum_layer):
    """Verify that binding is perfectly invertible."""
    # Create test vectors
    v1 = quantum_layer.random_vector()
    v2 = quantum_layer.random_vector()

    # Bind vectors
    bound = quantum_layer.bind(v1, v2)

    # Unbind and verify recovery
    recovered = quantum_layer.unbind(bound, v2)
    cosine_sim = quantum_layer.cosine(v1, recovered)
    assert cosine_sim > 0.99


def test_role_orthogonality(quantum_layer):
    """Verify that different role vectors are approximately orthogonal."""
    role1 = quantum_layer.make_unitary_role("role::1")
    role2 = quantum_layer.make_unitary_role("role::2")

    # Calculate cosine similarity
    cosine_sim = quantum_layer.cosine(role1, role2)
    assert abs(cosine_sim) < 0.1


def test_density_matrix_properties():
    """Verify PSD and trace properties of density matrix."""
    dim = 1024
    rho = DensityMatrix(dim)

    # Create random fillers
    fillers = np.random.randn(10, dim)
    fillers /= np.linalg.norm(fillers, axis=1)[:, None]

    # Update density matrix
    rho.update(fillers)

    # Verify PSD property
    assert rho.is_psd(), "Density matrix must be positive semi-definite"

    # Verify trace normalization
    assert_allclose(rho.trace(), 1.0, rtol=1e-5)


def test_superposition_properties(quantum_layer):
    """Verify properties of vector superposition."""
    v1 = quantum_layer.random_vector()
    v2 = quantum_layer.random_vector()

    # Test superposition
    sup = quantum_layer.superpose(v1, v2)

    # Verify unit norm
    norm = np.linalg.norm(sup)
    assert_allclose(norm, 1.0, rtol=1e-5)


def test_binding_associativity(quantum_layer):
    """Verify binding associativity property."""
    a = quantum_layer.random_vector()
    b = quantum_layer.random_vector()
    c = quantum_layer.random_vector()

    # Test (a * b) * c = a * (b * c)
    bound1 = quantum_layer.bind(quantum_layer.bind(a, b), c)
    bound2 = quantum_layer.bind(a, quantum_layer.bind(b, c))

    cosine_sim = quantum_layer.cosine(bound1, bound2)
    assert_allclose(cosine_sim, 1.0, rtol=1e-4)


def test_binding_distributivity(quantum_layer):
    """Verify binding distributivity over superposition."""
    a = quantum_layer.random_vector()
    b = quantum_layer.random_vector()
    c = quantum_layer.random_vector()

    # Test a * (b + c) = (a * b) + (a * c)
    left = quantum_layer.bind(a, quantum_layer.superpose(b, c))
    right = quantum_layer.superpose(quantum_layer.bind(a, b), quantum_layer.bind(a, c))

    cosine_sim = quantum_layer.cosine(left, right)
    assert_allclose(cosine_sim, 1.0, rtol=1e-4)


def test_permutation_cycle(quantum_layer):
    """Verify that permutation cycles properly."""
    v = quantum_layer.random_vector()

    # Apply permutation n times
    n = quantum_layer.cfg.dim
    permuted = quantum_layer.permute(v, times=n)

    # Should return to original vector
    cosine_sim = quantum_layer.cosine(v, permuted)
    assert_allclose(cosine_sim, 1.0, rtol=1e-4)
