import numpy as np

from somabrain.agent_memory import MEMORY_STORE, encode_memory, recall_memory
from somabrain.schemas import Observation


def test_encode_and_recall_top1():
    MEMORY_STORE.clear()
    obs = Observation(
        who="u",
        where="here",
        when="2025-01-01T00:00:00Z",
        channel="test",
        content="alpha",
        embeddings=list(np.random.randn(2048).astype("float32")),
        traceId="t1",
        tags=[],
    )
    m = encode_memory(obs)
    # query is the same vector; expect to recall it
    res = recall_memory(m.vector, top_k=1)
    assert len(res) == 1
    assert res[0].id == m.id
