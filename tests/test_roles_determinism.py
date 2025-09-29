import numpy as np
from somabrain.quantum import HRRConfig, make_quantum_layer
from somabrain.numerics import rfft_norm

DIM = 256
SEED = 123

def test_role_determinism_and_spectrum_symmetry():
    cfg = HRRConfig(dim=DIM, seed=SEED)
    q = make_quantum_layer(cfg)
    role_a1 = q.make_unitary_role("deterministic-token")
    role_a2 = q.make_unitary_role("deterministic-token")
    assert np.allclose(role_a1, role_a2, atol=1e-7)
    H = rfft_norm(role_a1, n=DIM)
    # DC always real
    assert abs(H[0].imag) < 1e-12
    if DIM % 2 == 0:
        # Nyquist bin real
        assert abs(H[-1].imag) < 1e-12
    # Magnitudes ~1
    assert np.allclose(np.abs(H), 1.0, atol=2e-5)


def test_text_encoding_determinism():
    cfg = HRRConfig(dim=DIM, seed=SEED)
    q = make_quantum_layer(cfg)
    v1 = q.encode_text("the-same-sentence")
    v2 = q.encode_text("the-same-sentence")
    assert np.allclose(v1, v2, atol=1e-7)
