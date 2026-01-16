"""Fractal Client Adapter - Enforcing Single Point of Access.

VIBE Compliance:
    - Rule #1: No Bullshit (No mocks, direct usage of MemoryClient).
    - Rule #4: Real Implementations Only (Routes to real HTTP service).

This adapter translates the Brain's semantic interface (encode_fractal, retrieve_fractal)
into standard Memory Service operations (remember, recall), ensuring that the
UnifiedBrainCore uses the centralized MemoryClient lane strictly.
"""

from typing import Any, Dict, List, Tuple

from somabrain.memory_client import MemoryClient


class FractalClientAdapter:
    """Adapter to route UnifiedBrainCore operations through MemoryClient.

    This ensures strict Single Point of Access (SPoA) for all memory operations,
    preventing the Brain from opening direct "backdoor" connections to the database.
    """

    def __init__(self, client: MemoryClient):
        """Initialize the instance."""

        self.client = client

    def encode_fractal(self, content: Dict[str, Any], importance: float = 1.0) -> List[Any]:
        """Persist content via the Memory Service.

        Translates the Brain's 'fractal encoding' request into a standard 'remember' call.

        Args:
            content: The memory payload.
            importance: Importance score.

        Returns:
            List of 'nodes' (simulated by returning the stored coordinate wrapped in a list)
            to satisfy the UnifiedBrainCore's expectation of a list return.
        """
        # We use a deterministic key based on content or uuid if not present
        # In a real fractal system we'd generate a specific key, here we trust the Service
        key = content.get("id") or content.get("task_id") or "fractal_trace"

        # Enrich payload with 'fractal' specific metadata if needed
        payload = content.copy()
        payload["_system"] = "unified_brain_fractal"
        payload["_importance"] = importance

        # PERSIST: Single Point of Access call
        coord = self.client.remember(str(key), payload)

        # UnifiedBrainCore expects a list of 'nodes'.
        # We return the coordinate as a single 'node' trace.
        # This adapts the interface without changing the Brain's logic flow yet.
        return [coord]

    def retrieve_fractal(self, query: Dict[str, Any], top_k: int = 3) -> List[Tuple[Any, float]]:
        """Retrieve memories via the Memory Service.

        Translates Brain's 'retrieve_fractal' to 'recall'.

        Args:
            query: Query dictionary (Brain uses dicts).
            top_k: Number of results.

        Returns:
            List of (content_trace, score) tuples.
        """
        # Convert dictionary query to string for standard Memory Client recall
        # Logic: use 'content' or 'text' field, or dump json
        q_str = query.get("text") or query.get("content") or str(query)

        # RETRIEVE: Single Point of Access call
        hits = self.client.recall(q_str, top_k=top_k)

        # Adapt hits to (node, resonance) tuples expected by UnifiedBrainCore
        results = []
        for hit in hits:
            # Hit object from MemoryClient has .payload, .score
            # UnifiedBrainCore expects an object with .memory_trace attribute (see view_file earlier)
            # We create a simple wrapper or just pass the payload if checking source code allows.
            # Checking UnifiedBrainCore._combine_results:
            #   for i, (node, resonance) in enumerate(fractal_results):
            #       combined.append({"content": node.memory_trace, ...})

            # So 'node' must be an object with 'memory_trace' attribute.
            class AdapterNode:
                """Adapternode class implementation."""

                def __init__(self, p):
                    """Initialize the instance."""

                    self.memory_trace = p

            results.append((AdapterNode(hit.payload), hit.score))

        return results
