"""Sphinx stub for somabrain.api.routers.rag

Contains a minimal retrieve API surface for documentation only.
"""

from typing import Any, Dict, List


def retrieve(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """Run a retrieval-augmented generation query (stub).

    Returns a list of candidate documents in a simplified shape.
    """
    return [{"doc_id": "stub", "score": 0.0, "snippet": "stub"}]
