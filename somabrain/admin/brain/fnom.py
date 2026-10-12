"""Persistent FNOM — MemoryClient-only (T-1 single lane).

VIBE Compliance:
    - Rule #4: Real Implementations Only.
    - Rule #1: No Bullshit (no stubs, no second DB/Milvus lanes).
    - Rule #5: Documentation = Truth.

T-1 / B29: all persistence goes through MemoryClient → SFM → Milvus/Postgres.
FNOM never opens Milvus, Postgres, or any store directly.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("somabrain.brain.fnom")


@dataclass
class FNOMResult:
    """Result object compatible with UnifiedBrainCore expectations."""

    frequency_spectrum: list[float]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class FNOMTrace:
    """Trace object for retrieval results."""

    content: dict[str, Any]
    similarity: float


class PersistentFNOM:
    """FNOM facade over the single MemoryClient lane (SFM is the only store)."""

    def __init__(
        self,
        client: Any,
        namespace: str = "fnom",
        embedder: Any = None,
    ):
        """Initialize PersistentFNOM on the SFM MemoryClient.

        Args:
            client: MemoryClient (sole SFM gateway).
            namespace: Logical namespace label for payloads.
            embedder: Optional embedder (unused for persistence; SFM embeds).
        """
        self.client = client
        self.namespace = namespace
        self.embedder = embedder

    def encode(self, content: dict[str, Any], importance: float = 1.0) -> FNOMResult:
        """Persist content through MemoryClient and return a stable spectrum.

        The spectrum is a deterministic cognitive summary of the content; the
        durable write is always MemoryClient.remember (SFM owns Milvus).
        """
        import hashlib
        import json
        import math

        payload = dict(content)
        payload["_system"] = "fnom"
        payload["_namespace"] = self.namespace
        key = str(
            content.get("id")
            or content.get("task_id")
            or content.get("coord")
            or hashlib.sha256(
                json.dumps(payload, sort_keys=True, default=str).encode()
            ).hexdigest()
        )
        self.client.remember(key, payload)

        raw = json.dumps(payload, sort_keys=True, default=str)
        digest = hashlib.sha256(raw.encode()).digest()
        spectrum = [
            (digest[i] / 255.0) * float(importance) * math.sin(i * 0.1 + 1.0)
            for i in range(min(16, len(digest)))
        ]
        return FNOMResult(
            frequency_spectrum=spectrum,
            metadata={"namespace": self.namespace, "importance": importance},
        )

    def retrieve(
        self, query: dict[str, Any], top_k: int = 3
    ) -> list[tuple[FNOMTrace, float]]:
        """Recall through MemoryClient (never a second vector lane)."""
        q = query.get("text") or query.get("content") or str(query)
        hits = self.client.recall(q, top_k=top_k)
        out: list[tuple[FNOMTrace, float]] = []
        for hit in hits or []:
            payload = getattr(hit, "payload", None)
            if payload is None and isinstance(hit, dict):
                payload = hit.get("payload") or hit
            score = float(getattr(hit, "score", 0.0) if not isinstance(hit, dict) else hit.get("score", 0.0))
            out.append((FNOMTrace(content=payload or {}, similarity=score), score))
        return out
