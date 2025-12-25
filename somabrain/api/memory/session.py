"""Session Store for Memory API.

This module contains the RecallSessionStore class for managing
recall sessions with TTL-based expiration.
"""

from __future__ import annotations

import time
from threading import RLock
from typing import Any, Dict, List, Optional

from somabrain.core.container import container


class RecallSessionStore:
    """Thread-safe store for recall sessions with TTL-based expiration.

    This class encapsulates the session management logic that was previously
    using module-level global state. Sessions are stored in-memory with
    automatic pruning of expired entries.

    Thread Safety:
        All operations are protected by a reentrant lock to ensure thread safety.
    """

    def __init__(self, ttl_seconds: int = 900) -> None:
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._lock = RLock()
        self._ttl_seconds = ttl_seconds

    def store(
        self,
        session_id: str,
        tenant: str,
        namespace: str,
        conversation_id: Optional[str],
        scoring_mode: Optional[str],
        results: List[Any],
    ) -> None:
        """Store a recall session with results."""
        payload = {
            "session_id": session_id,
            "tenant": tenant,
            "namespace": namespace,
            "conversation_id": conversation_id,
            "scoring_mode": scoring_mode,
            "created_at": time.time(),
            "results": [
                item.dict() if hasattr(item, "dict") else item for item in results
            ],
        }
        with self._lock:
            self._sessions[session_id] = payload

    def get(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get a session by ID, or None if not found."""
        with self._lock:
            return self._sessions.get(session_id)

    def prune(self) -> None:
        """Remove expired sessions."""
        now = time.time()
        with self._lock:
            expired = [
                session_id
                for session_id, state in self._sessions.items()
                if now - state.get("created_at", 0.0) > self._ttl_seconds
            ]
            for session_id in expired:
                self._sessions.pop(session_id, None)

    def clear(self) -> None:
        """Clear all sessions (for testing)."""
        with self._lock:
            self._sessions.clear()


def _create_recall_session_store() -> RecallSessionStore:
    """Factory function for DI container registration."""
    return RecallSessionStore(ttl_seconds=900)


# Register with DI container
container.register("recall_session_store", _create_recall_session_store)


def get_recall_session_store() -> RecallSessionStore:
    """Get the recall session store from the DI container."""
    return container.get("recall_session_store")


__all__ = [
    "RecallSessionStore",
    "get_recall_session_store",
]
