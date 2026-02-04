"""
Agent Memory Core
Contract-first encode, recall, and consolidate logic for the agent brain using canonical schemas.
Implements: unit-norm validation, cosine recall, and weighted merge with simple SNR reporting.
"""

from __future__ import annotations

from typing import Any, List, Optional, Tuple, cast

import numpy as np

from somabrain.math import cosine_similarity
from somabrain.schemas import Memory, Observation, Thought


def _get_settings():
    """Lazy settings access to avoid circular imports."""
    from django.conf import settings

    return settings


# In-memory store for demonstration (replace with DB/service in production)
MEMORY_STORE: List[Memory] = []


def _to_unit(vec: Any) -> Any:
    """
    Pad/truncate to global hrr_dim and unit-normalize (hrr_dtype).
    Enforces mathematical invariant: all vectors are unit-norm, hrr_dtype, and reproducible.
    """
    from somabrain.math import normalize_vector

    s = _get_settings()
    hrr_dim = s.SOMABRAIN_HRR_DIM
    hrr_dtype = s.SOMABRAIN_HRR_DTYPE

    v = cast(np.ndarray, np.asarray(vec, dtype=hrr_dtype).reshape(-1))
    if v.size != hrr_dim:
        if v.size < hrr_dim:
            v = np.pad(v, (0, hrr_dim - v.size))
        else:
            v = v[:hrr_dim]
    return normalize_vector(v, dtype=np.dtype(hrr_dtype))


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
        strength=1.0,
    )
    MEMORY_STORE.append(mem)
    return mem


# --- Recall (retrieve memory) ---
def recall_memory(query_vector: List[float], top_k: int = 3) -> List[Memory]:
    """Retrieve top_k memories most similar to the query_vector (cosine)."""
    if top_k is None:
        top_k = 3
    try:
        top_k = max(0, int(top_k))
    except Exception:
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
        s = cosine_similarity(q, v)
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
            strength=float(max(1e-6, float(m.strength))),
        )
        MEMORY_STORE.append(consolidated)
        return consolidated
    weights = np.asarray(
        [max(1e-6, float(m.strength)) for m in memories], dtype=np.float32
    )
    # mypy's numpy type hints are strict about array shape typing here; the runtime
    # behavior is correct and we normalize shapes via _to_unit — silence the
    # complaint for now and consider a more precise typing later.
    # np.stack here produces an ndarray with runtime shape (N, HRR_DIM). The
    # numpy type hints are strict about tuple shapes; the runtime behavior is
    # correct and validated by _to_unit. Silence the precise shape typing
    # complaint for now with a narrow ignore.
    vecs = np.stack(
        [_to_unit(np.asarray(m.vector, dtype=np.float32)) for m in memories], axis=0
    )
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
        strength=float(weights.mean()),
    )
    MEMORY_STORE.append(consolidated)
    return consolidated


# --- Store Memory Item (for BrainBridge integration) ---
async def store_memory_item(content: str, **kwargs) -> dict:
    """Store a memory item asynchronously.

    This is the entry point for BrainBridge.remember() in AAAS Direct mode.

    Args:
        content: Text content to store
        **kwargs: Metadata including:
            - tenant: Tenant ID
            - namespace: Memory namespace (default: "episodic")
            - metadata: Additional metadata dict

    Returns:
        Dict containing:
            - memory_id: UUID of the stored memory
            - coordinate: Retrieval coordinate for the memory
    """
    import hashlib
    from uuid import uuid4

    from somabrain.schemas import Observation

    # Extract metadata
    namespace = kwargs.get("namespace", "episodic")
    metadata = kwargs.get("metadata", {})
    tenant = kwargs.get("tenant", "default")

    # Generate coordinate (deterministic for dedup, includes content hash)
    content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
    memory_id = str(uuid4())
    coordinate = f"{namespace}:{tenant}:{content_hash}"

    # Create observation and generate real embedding
    # This calls the quantum layer to produce the vector embedding
    s = _get_settings()
    dim = getattr(s, "SOMABRAIN_HRR_DIM", 256)

    # Generate embedding via quantum layer if available
    try:
        from somabrain.admin.core.quantum import HRRConfig, QuantumLayer

        quantum = QuantumLayer(HRRConfig(dim=dim))
        embedding = quantum.encode_text(content).tolist()
    except Exception as e:
        # VIBE FIX: No zero vector fallback - fail loudly
        # Per Vibe Coding Rules: NO FAKES, NO FAKE RETURNS, NO HARDCODED VALUES
        raise RuntimeError(
            f"Failed to generate embedding for content: {e}. "
            "Embedding is REQUIRED for memory storage. "
            "Check quantum layer or embedder configuration."
        ) from e


    obs = Observation(
        type="text",
        content=content,
        embeddings=embedding,
        metadata={
            "coordinate": coordinate,
            "tenant": tenant,
            "namespace": namespace,
            **metadata,
        },
    )

    # Store via encode_memory
    mem = encode_memory(obs)

    return {
        "memory_id": memory_id,
        "coordinate": coordinate,
        "vector_id": mem.id,
    }


# --- Test/maintenance helpers ---
def clear_memory_store() -> None:
    """Clear the in-memory store (for tests)."""
    MEMORY_STORE.clear()

