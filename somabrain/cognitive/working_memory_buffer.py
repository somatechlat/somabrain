"""Session-based working memory buffer for trace recording.

Provides a simple in-memory storage for cognitive traces per session, used
by the ContextBuilder.
"""

from __future__ import annotations

from typing import Any, Dict, List


class WorkingMemoryBuffer:
    """Lightweight session-indexed storage for cognitive traces."""

    def __init__(self, max_items_per_session: int = 10):
        """Initialize the instance."""

        self._store: Dict[str, List[Dict[str, Any]]] = {}
        self._max_items = max_items_per_session

    def record(self, session_id: str, item: Dict[str, Any]) -> None:
        """Record an item to the session trace."""
        if not session_id:
            return
        if session_id not in self._store:
            self._store[session_id] = []
        
        self._store[session_id].append(item)
        
        # Enforce capacity limit
        if len(self._store[session_id]) > self._max_items:
            self._store[session_id].pop(0)

    def snapshot(self, session_id: str) -> List[Dict[str, Any]]:
        """Return the current trace for a session."""
        if not session_id:
            return []
        return list(self._store.get(session_id, []))

    def clear_session(self, session_id: str) -> None:
        """Clear the trace for a session."""
        self._store.pop(session_id, None)