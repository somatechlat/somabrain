import pytest

from somabrain.quantum import HRRConfig, QuantumLayer


@pytest.mark.parametrize("dim", [2048, 8192])
@pytest.mark.parametrize("dtype", ["float32", "float64"])
def test_bind_unbind_regression(dim, dtype):
    cfg = HRRConfig(dim=dim, seed=123, renorm=True)
    cfg.dtype = dtype
    q = QuantumLayer(cfg)
    a = q.random_vector()
    b = q.random_vector()
    ab = q.bind(a, b)
    a_rec = q.unbind(ab, b)
    cos = q.cosine(a, a_rec)
    assert cos > 0.8, f"recovery cos={cos} for dim={dim},dtype={dtype}"
