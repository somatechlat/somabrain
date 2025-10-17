from __future__ import annotations

import numpy as np

from somabrain.quantum import HRRConfig, QuantumLayer


def _random_quantum(dim: int = 128, seed: int = 7) -> QuantumLayer:
    cfg = HRRConfig(dim=dim, seed=seed, roles_unitary=True)
    return QuantumLayer(cfg)


def test_unitary_roles_are_norm_preserving_and_deterministic():
    q = _random_quantum(dim=128, seed=11)

    role_a = q.make_unitary_role("alpha")
    role_b = q.make_unitary_role("beta")
    role_a_second = q.make_unitary_role("alpha")

    assert np.isclose(np.linalg.norm(role_a), 1.0, atol=1e-6)
    assert np.allclose(role_a, role_a_second)
    assert abs(QuantumLayer.cosine(role_a, role_b)) < 0.075


def test_unitary_role_spectrum_has_unit_magnitude():
    q = _random_quantum(dim=96, seed=19)
    q.make_unitary_role("spectrum")

    cached = q._role_fft_cache["spectrum"]  # noqa: SLF001 - intentional for validation
    magnitudes = np.abs(cached)

    assert np.allclose(magnitudes, 1.0, atol=1e-3)


def test_bind_unbind_roundtrip_accuracy_high():
    cfg = HRRConfig(dim=192, seed=23)
    q = QuantumLayer(cfg)

    lhs = q.random_vector()
    rhs = q.random_vector()

    bound = q.bind(lhs, rhs)
    recovered = q.unbind(bound, rhs)

    assert QuantumLayer.cosine(lhs, recovered) > 0.995
