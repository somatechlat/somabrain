from __future__ import annotations
from typing import Any, List, Optional, Tuple, cast
import numpy as np
from somabrain.nano_profile import HRR_DIM, HRR_DTYPE
from somabrain.schemas import Memory, Observation, Thought
from common.logging import logger

"""
Agent Memory Core
Contract-first encode, recall, and consolidate logic for the agent brain using canonical schemas.
Implements: unit-norm validation, cosine recall, and weighted merge with simple SNR reporting.
"""





# In-memory store for demonstration (replace with DB/service in production)
MEMORY_STORE: List[Memory] = []


def _to_unit(vec: Any) -> Any:
    """
    Pad/truncate to global HRR_DIM and unit-normalize (HRR_DTYPE).
    Enforces mathematical invariant: all vectors are unit-norm, HRR_DTYPE, and reproducible.
    """
    # mypy's numpy stubs are strict about ndarray shape annotations; cast the
    # runtime result to a generic ndarray to avoid shape-token complaints.
    v = cast(np.ndarray, np.asarray(vec, dtype=HRR_DTYPE).reshape(-1))
    if v.size != HRR_DIM:
        if v.size < HRR_DIM:
            v = np.pad(v, (0, HRR_DIM - v.size))
        else:
            v = v[:HRR_DIM]
    n = float(np.linalg.norm(v))
    dtype = np.dtype(HRR_DTYPE)
    tiny_floor = float(np.finfo(dtype).eps) * max(1.0, float(HRR_DIM))
    if n < tiny_floor:
        # Return zero vector of expected shape
        return np.zeros((HRR_DIM,), dtype=HRR_DTYPE)  # type: ignore[return-value]
    return (v / n).astype(HRR_DTYPE)


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    na = float(np.linalg.norm(a))
    nb = float(np.linalg.norm(b))
    if na <= 0 or nb <= 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


# --- Encode (store memory) ---
def encode_memory(obs: Observation, thought: Optional[Thought] = None) -> Memory:
    """Encode an Observation (+ optional Thought) into episodic Memory and store it."""
    # Defensive guard: ensure embeddings are list-like and numeric
    if not isinstance(obs.embeddings, (list, tuple)):
        raise TypeError("Observation.embeddings must be a list[float]")
    vec = _to_unit(np.array(obs.embeddings, dtype=np.float32))
    payload = {"observation": obs.dict()}
    if thought is not None:
        payload["thought"] = thought.dict()
    mem = Memory(
        id=f"mem-{len(MEMORY_STORE) + 1}",
        type="episodic",
        vector=vec.tolist(),
        graphRefs=[],
        payload=payload,
        strength=1.0, )
    MEMORY_STORE.append(mem)
    return mem


# --- Recall (retrieve memory) ---
def recall_memory(query_vector: List[float], top_k: int = 3) -> List[Memory]:
    """Retrieve top_k memories most similar to the query_vector (cosine)."""
    if top_k is None:
        top_k = 3
    try:
        pass
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise
        top_k = max(0, int(top_k))
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise
        top_k = 3
    if not MEMORY_STORE or top_k == 0:
        return []
    if not isinstance(query_vector, (list, tuple, np.ndarray)):
        return []
    q = _to_unit(np.asarray(query_vector, dtype=np.float32))
    scored: List[Tuple[Memory, float]] = []
    for mem in MEMORY_STORE:
        v = np.asarray(mem.vector, dtype=np.float32)
        v = _to_unit(v)
        s = _cosine(q, v)
        scored.append((mem, s))
    scored.sort(key=lambda x: x[1], reverse=True)
    return [m for m, _ in scored[:top_k]]


# --- Consolidate (update/merge memories) ---
def consolidate_memories(memories: List[Memory]) -> Memory:
    """Weighted merge by strength; renorm; payload merged under keys; returns semantic Memory."""
    if not memories:
        raise ValueError("No memories to consolidate.")
    if len(memories) == 1:
        # Return a semantic clone with normalized vector and same payload
        m = memories[0]
        avg = _to_unit(np.asarray(m.vector, dtype=np.float32))
        consolidated = Memory(
            id=f"sem-{len(MEMORY_STORE) + 1}",
            type="semantic",
            vector=avg.tolist(),
            graphRefs=[],
            payload={"mem_0": m.payload},
            strength=float(max(1e-6, float(m.strength))), )
        MEMORY_STORE.append(consolidated)
        return consolidated
    weights = np.asarray(
        [max(1e-6, float(m.strength)) for m in memories], dtype=np.float32
    )
    # mypy's numpy stubs are strict about array shape typing here; the runtime
    # behavior is correct and we normalize shapes via _to_unit — silence the
    # complaint for now and consider a more precise typing later.
    # np.stack here produces an ndarray with runtime shape (N, HRR_DIM). The
    # numpy type stubs are strict about tuple shapes; the runtime behavior is
    # correct and validated by _to_unit. Silence the precise shape typing
    # complaint for now with a narrow ignore.
    vecs = np.stack(
        [_to_unit(np.asarray(m.vector, dtype=np.float32)) for m in memories], axis=0
    )  # type: ignore[arg-type]
    w = weights / float(weights.sum())
    avg = (w[:, None] * vecs).sum(axis=0)
    avg = _to_unit(avg)

    merged_payload = {f"mem_{i}": m.payload for i, m in enumerate(memories)}
    consolidated = Memory(
        id=f"sem-{len(MEMORY_STORE) + 1}",
        type="semantic",
        vector=avg.tolist(),
        graphRefs=[],
        payload=merged_payload,
        strength=float(weights.mean()), )
    MEMORY_STORE.append(consolidated)
    return consolidated


# --- Test/maintenance helpers ---
def clear_memory_store() -> None:
    """Clear the in-memory store (for tests)."""
    MEMORY_STORE.clear()
