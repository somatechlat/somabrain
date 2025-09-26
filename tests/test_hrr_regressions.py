import pytest

from somabrain.quantum import HRRConfig, QuantumLayer


@pytest.mark.parametrize("dim", [2048, 8192])
@pytest.mark.parametrize("dtype", ["float32", "float64"])
@pytest.mark.parametrize("beta", [0.0, 1e-8, 1e-6])
def test_bind_unbind_regression(dim, dtype, beta):
    cfg = HRRConfig(dim=dim, seed=123, renorm=True)
    cfg.dtype = dtype
    cfg.beta = beta
    q = QuantumLayer(cfg)
    a = q.random_vector()
    b = q.random_vector()
    ab = q.bind(a, b)
    a_rec = q.unbind(ab, b)
    cos = q.cosine(a, a_rec)
    # Conservative thresholds: recommended params (beta=1e-6) should be high
    if beta >= 1e-6 and dtype == "float32":
        assert (
            cos > 0.97
        ), f"low recovery cos={cos} for dim={dim},dtype={dtype},beta={beta}"
    else:
        assert cos > 0.8, f"recovery cos={cos} for dim={dim},dtype={dtype},beta={beta}"
