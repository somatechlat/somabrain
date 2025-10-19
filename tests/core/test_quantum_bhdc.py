import math

import numpy as np
import pytest

from somabrain.quantum import HRRConfig, QuantumLayer


@pytest.fixture(scope="module")
def quantum_layer() -> QuantumLayer:
    cfg = HRRConfig(dim=2048, seed=7, renorm=True, sparsity=0.1)
    return QuantumLayer(cfg)


def test_random_vector_is_unit_norm(quantum_layer: QuantumLayer) -> None:
    vec = quantum_layer.random_vector()
    assert vec.shape == (quantum_layer.cfg.dim,)
    norm = float(np.linalg.norm(vec))
    assert abs(norm - 1.0) < 1e-6


def test_bind_unbind_round_trip(quantum_layer: QuantumLayer) -> None:
    a = quantum_layer.encode_text("alpha vector")
    b = quantum_layer.encode_text("beta vector")
    bound = quantum_layer.bind(a, b)
    recovered = quantum_layer.unbind(bound, b)
    cosine = QuantumLayer.cosine(a, recovered)
    assert cosine > 0.95


def test_unitary_roles_are_deterministic(quantum_layer: QuantumLayer) -> None:
    role = quantum_layer.make_unitary_role("role::context")
    same_role = quantum_layer.make_unitary_role("role::context")
    assert np.allclose(role, same_role, atol=1e-7)
    spectrum = np.fft.rfft(role)
    magnitudes = np.abs(spectrum)
    assert np.allclose(magnitudes, 1.0, atol=5e-4)


def test_permutation_inverse_is_identity(quantum_layer: QuantumLayer) -> None:
    vec = quantum_layer.random_vector()
    permuted = quantum_layer.permute(vec, times=19)
    restored = quantum_layer.permute(permuted, times=-19)
    assert np.allclose(vec, restored, atol=1e-6)


def test_superposition_preserves_energy(quantum_layer: QuantumLayer) -> None:
    components = [quantum_layer.random_vector() for _ in range(8)]
    superposed = quantum_layer.superpose(components)
    norm = float(np.linalg.norm(superposed))
    assert abs(norm - 1.0) < 1e-6
    overlaps = [abs(float(np.dot(superposed, comp))) for comp in components]
    assert max(overlaps) < 0.75
