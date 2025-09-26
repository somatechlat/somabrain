"""
Tests for somabrain.agent_memory contract: encode, recall, consolidate guardrails.
"""

from importlib import import_module

import numpy as np


def test_encode_and_recall_happy():
    agent_mem = import_module("somabrain.agent_memory")
    schemas = import_module("somabrain.schemas")

    agent_mem.clear_memory_store()

    # Create observation shorter than HRR_DIM; validator will pad+renorm
    obs = schemas.Observation(
        who="u1",
        where="earth",
        when="2025-09-02T00:00:00Z",
        channel="text",
        content="hello world",
        embeddings=[0.1, 0.2, 0.3],
        tags=["t1"],
        traceId="trace-1",
    )
    thought = schemas.Thought(
        id="th1", causeIds=[], text="reflect", vector=[0.4, 0.5], uncertainty=0.1
    )
    m = agent_mem.encode_memory(obs, thought)
    assert m.id.startswith("mem-")
    assert (
        isinstance(m.vector, list)
        and len(m.vector) == import_module("somabrain.nano_profile").HRR_DIM
    )

    # Query close to obs.embeddings should recall it
    q = np.array(obs.embeddings, dtype=np.float32).tolist()
    hits = agent_mem.recall_memory(q, top_k=1)
    assert len(hits) == 1
    assert hits[0].id == m.id


def test_recall_invalid_query_and_topk():
    agent_mem = import_module("somabrain.agent_memory")
    agent_mem.clear_memory_store()
    # Invalid query types should return [] and not raise
    assert agent_mem.recall_memory("not-a-vector", top_k=3) == []
    assert agent_mem.recall_memory([], top_k=0) == []


def test_consolidate_single_and_multi():
    agent_mem = import_module("somabrain.agent_memory")
    schemas = import_module("somabrain.schemas")
    agent_mem.clear_memory_store()

    # Single memory consolidation becomes semantic clone
    base = schemas.Memory(
        id="m1",
        type="episodic",
        vector=[1.0, 0.0],
        graphRefs=[],
        payload={"a": 1},
        strength=0.5,
    )
    cm = agent_mem.consolidate_memories([base])
    assert cm.type == "semantic"
    assert (
        isinstance(cm.vector, list)
        and len(cm.vector) == import_module("somabrain.nano_profile").HRR_DIM
    )
    assert "mem_0" in cm.payload

    # Multi memory consolidation computes weighted average
    m2 = schemas.Memory(
        id="m2",
        type="episodic",
        vector=[0.0, 1.0],
        graphRefs=[],
        payload={"b": 2},
        strength=1.5,
    )
    cm2 = agent_mem.consolidate_memories([base, m2])
    assert cm2.type == "semantic"
    assert isinstance(cm2.strength, float) and cm2.strength > 0.0
