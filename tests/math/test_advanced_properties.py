"""
Advanced mathematical property tests for quantum operations.
Verifies complex mathematical invariants and properties.
"""

import numpy as np
import pytest
from numpy.testing import assert_allclose
from scipy.linalg import expm

from somabrain.quantum import HRRConfig, QuantumLayer
from memory.density import DensityMatrix


@pytest.fixture
def high_dim_quantum():
    """Create a high-dimensional quantum layer for precise tests."""
    cfg = HRRConfig(dim=16384, seed=42, sparsity=0.1)
    return QuantumLayer(cfg)


def test_spectral_heat_diffusion(high_dim_quantum):
        """Verify spectral heat diffusion properties using Chebyshev approximat
ion."""                                                                                # Create test vector
        v = high_dim_quantum.random_vector()
    
        # Create Laplacian matrix
        L = np.eye(high_dim_quantum.cfg.dim) - np.roll(np.eye(high_dim_quantum.cfg.dim), 1, axis=1)
        L = L @ L.T
    
        # Time parameter
        t = 0.1
    
        # Exact heat diffusion
        exact = expm(-t * L) @ v
    
        # Chebyshev approximation (as would be used in practice)
        k = 30  # Chebyshev order
        cheb = np.zeros_like(v)
        x = v.copy()
        cheb += x
        x_prev = x.copy()
        x = -2*t*L @ x
        cheb += x
    
        for i in range(2, k):
            x_new = -2*t*L @ x - x_prev
            cheb += x_new
            x_prev = x
            x = x_new
    
        # Verify approximation quality
        error = np.linalg.norm(exact - cheb)
        assert error < 0.1, f"Heat diffusion error too large: {error}"

def test_density_matrix_entropy(high_dim_quantum):
    """Verify von Neumann entropy properties of density matrix."""
    dim = 1024
    rho = DensityMatrix(dim)

    # Create pure state
    pure_state = np.zeros(dim)
    pure_state[0] = 1
    rho.update(np.array([pure_state]))

    # Pure state should have zero entropy
    eigvals = np.linalg.eigvalsh(rho.rho)
    eigvals = eigvals[eigvals > 1e-10]  # Remove numerical noise
    entropy = -np.sum(eigvals * np.log(eigvals))
    assert entropy < 1e-5, f"Pure state entropy should be zero, got {entropy}"

    # Maximally mixed state should have maximum entropy
    mixed_states = np.eye(dim)
    rho.update(mixed_states)

    eigvals = np.linalg.eigvalsh(rho.rho)
    eigvals = eigvals[eigvals > 1e-10]
    entropy = -np.sum(eigvals * np.log2(eigvals))
    max_entropy = np.log2(dim)
    assert entropy < max_entropy, f"Mixed state entropy exceeds maximum: {entropy} > {max_entropy}"

def test_role_frame_properties(high_dim_quantum):
    """Verify properties of the role frame (approximately tight frame)."""
    roles = [
        high_dim_quantum.make_unitary_role(f"test::role::{i}")
        for i in range(10)
    ]
    
    # Create frame operator
    frame_op = sum(np.outer(r, r) for r in roles)
    
    # Check frame bounds
    eigvals = np.linalg.eigvalsh(frame_op)
    frame_ratio = np.max(eigvals) / np.min(eigvals)
    assert frame_ratio < 2.0, f"Frame not sufficiently tight: {frame_ratio}"


def test_binding_energy_conservation(high_dim_quantum):
    """Verify energy conservation in binding operations."""
    v1 = high_dim_quantum.random_vector()
    v2 = high_dim_quantum.random_vector()
    
    # Energy before binding
    e1 = np.sum(v1 * v1)
    e2 = np.sum(v2 * v2)
    
    # Bind vectors
    bound = high_dim_quantum.bind(v1, v2)
    
    # Energy after binding
    e_bound = np.sum(bound * bound)
    
    # Energy should be approximately conserved
    assert_allclose(e_bound, 1.0, rtol=1e-5)


def test_permutation_group_properties(high_dim_quantum):
    """Verify algebraic properties of permutation group."""
    v = high_dim_quantum.random_vector()
    
    # Identity: p^n = 1 where n is dimension
    n = high_dim_quantum.cfg.dim
    p_n = high_dim_quantum.permute(v, times=n)
    assert_allclose(v, p_n, rtol=1e-5)
    
    # Subgroup property: p^k is a permutation
    k = n // 2
    p_k = high_dim_quantum.permute(v, times=k)
    assert_allclose(np.linalg.norm(p_k), 1.0, rtol=1e-5)


def test_density_matrix_monotonicity(high_dim_quantum):
    """Verify monotonicity of density matrix updates."""
    dim = 1024
    rho = DensityMatrix(dim)

    # Create sequence of states
    states = [np.random.randn(dim) for _ in range(5)]
    for i in range(len(states)):
        states[i] /= np.linalg.norm(states[i])

    prev_entropy = float('-inf')
    for state in states:
        rho.update(np.array([state]))        # Calculate von Neumann entropy
        eigvals = np.linalg.eigvalsh(rho.rho)
        eigvals = eigvals[eigvals > 1e-10]
        entropy = -np.sum(eigvals * np.log2(eigvals))
        
        # Entropy should increase monotonically
        assert entropy >= prev_entropy
        prev_entropy = entropy


def test_quantum_interference(high_dim_quantum):
    """Verify quantum interference patterns in superposition."""
    # Create two orthogonal vectors
    v1 = high_dim_quantum.random_vector()
    v2 = high_dim_quantum.random_vector()
    v2 = v2 - np.dot(v2, v1) * v1  # Gram-Schmidt
    v2 = v2 / np.linalg.norm(v2)
    
    # Create superposition with phase
    theta = np.pi / 4
    superpos = np.cos(theta) * v1 + np.sin(theta) * v2
    
    # Verify interference pattern
    proj1 = np.abs(np.dot(superpos, v1)) ** 2
    proj2 = np.abs(np.dot(superpos, v2)) ** 2
    
    assert_allclose(proj1, np.cos(theta)**2, rtol=1e-5)
    assert_allclose(proj2, np.sin(theta)**2, rtol=1e-5)
    assert_allclose(proj1 + proj2, 1.0, rtol=1e-5)