import numpy as np

from somabrain import schemas as S
from somabrain.nano_profile import HRR_DIM
from somabrain.quantum import HRRConfig, QuantumLayer


def test_hrr_vector_dim_and_norm():
    cfg = HRRConfig(dim=HRR_DIM, seed=123, renorm=True)
    q = QuantumLayer(cfg)
    v = q.encode_text("unit-test-vector")
    assert v.shape[0] == HRR_DIM
    n = float(np.linalg.norm(v))
    assert abs(n - 1.0) < 1e-6, f"vector not unit norm: {n}"


def test_bind_unbind_recovery():
    cfg = HRRConfig(dim=HRR_DIM, seed=7, renorm=True)
    q = QuantumLayer(cfg)
    a = q.random_vector()
    b = q.random_vector()
    ab = q.bind(a, b)
    a_rec = q.unbind(ab, b)
    # Recovery measured by cosine similarity; expect high overlap
    cos = q.cosine(a, a_rec)
    assert cos > 0.9, f"bind/unbind recovery too low: {cos}"


def test_superpose_normalized():
    cfg = HRRConfig(dim=HRR_DIM, seed=42, renorm=True)
    q = QuantumLayer(cfg)
    vecs = [q.random_vector() for _ in range(5)]
    s = q.superpose(vecs)
    n = float(np.linalg.norm(s))
    assert abs(n - 1.0) < 1e-6


def test_schema_observation_embeddings_normalized():
    # Create an observation with a deliberately small embedding and ensure
    # validator normalizes/pads
    small = [0.1] * min(4, HRR_DIM)
    obs = S.Observation(
        who="t",
        where="here",
        when="now",
        channel="c",
        content="x",
        embeddings=small,
        tags=[],
        traceId="t1",
    )
    emb = np.asarray(obs.embeddings, dtype=np.float32)
    assert emb.shape[0] == HRR_DIM
    n = float(np.linalg.norm(emb))
    # normalized to unit-norm
    assert abs(n - 1.0) < 1e-5
