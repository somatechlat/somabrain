import numpy as np
from somabrain.math.appr import appr_push
from somabrain.math.bridge import sinkhorn_bridge_from_embeddings


def test_appr_simple_chain():
    # chain graph 0-1-2-3
    adj = {
        0: [(1, 1.0)],
        1: [(0, 1.0), (2, 1.0)],
        2: [(1, 1.0), (3, 1.0)],
        3: [(2, 1.0)],
    }
    p = appr_push(adj, seed=0, alpha=0.85, eps=1e-6)
    # seed should have high score and neighbors smaller
    assert p[0] > 0.1


def test_bridge_embeddings_small():
    rng = np.random.default_rng(0)
    X = rng.normal(size=(8, 16))
    Y = rng.normal(size=(10, 16))
    P, err = sinkhorn_bridge_from_embeddings(X, Y, eps=1e-2, tol=1e-4)
    assert err < 1e-2
    # marginals
    assert np.allclose(P.sum(axis=1), np.ones(8) / 8, atol=1e-2)
    assert np.allclose(P.sum(axis=0), np.ones(10) / 10, atol=1e-2)
