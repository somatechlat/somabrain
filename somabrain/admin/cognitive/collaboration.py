"""
Collaboration manager – Phase 3 Cognitive Capability

Provides a very lightweight *multi‑agent coordination* layer.  The goal is to
expose a simple API that can be used by higher‑level components (e.g., the
Planner or the autonomous learning loop) to:

1. Register agents (identified by a unique string).
2. Send direct messages between agents.
3. Broadcast a message to all registered agents.
4. Retrieve the inbox of a given agent.

The implementation stores messages in an in‑memory ``dict`` mapping agent IDs to
queues of ``Message`` objects.  It is deliberately minimal – persistence,
security, and network transport are left for future extensions.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Message:
    """A simple message exchanged between agents.

    Attributes
    ----------
    sender: str
        Identifier of the sending agent.
    recipient: Optional[str]
        Identifier of the target agent; ``None`` indicates a broadcast.
    timestamp: datetime
        Time the message was created.
    payload: str
        Arbitrary text payload – in a real system this could be JSON or a
        serialized object.
    """

    sender: str
    recipient: Optional[str]
    timestamp: datetime
    payload: str

    def __repr__(self) -> str:  # pragma: no cover – trivial
        """Return object representation."""

        target = self.recipient if self.recipient else "*broadcast*"
        return f"Message(from={self.sender}, to={target}, payload={self.payload!r})"


class CollaborationManager:
    """Manages a set of agents and their message queues.

    The manager is *stateful* – it lives for the lifetime of the process.  It
    can be instantiated directly or accessed via a singleton pattern if the
    application prefers a global coordinator.
    """

    def __init__(self) -> None:
        """Initialize the instance."""

        self._agents: Dict[str, List[Message]] = {}
        logger.info("CollaborationManager initialised")

    # ------------------------------------------------------------------
    # Agent registration
    # ------------------------------------------------------------------
    def register_agent(self, agent_id: str) -> None:
        """Create an empty inbox for ``agent_id`` if it does not already exist."""
        if agent_id in self._agents:
            logger.debug("Agent %s already registered", agent_id)
            return
        self._agents[agent_id] = []
        logger.info("Registered agent %s", agent_id)

    def unregister_agent(self, agent_id: str) -> None:
        """Remove ``agent_id`` and discard any pending messages."""
        if agent_id in self._agents:
            del self._agents[agent_id]
            logger.info("Unregistered agent %s", agent_id)
        else:
            logger.warning("Attempted to unregister unknown agent %s", agent_id)

    # ------------------------------------------------------------------
    # Messaging primitives
    # ------------------------------------------------------------------
    def send(self, sender: str, recipient: str, payload: str) -> None:
        """Send a direct message from ``sender`` to ``recipient``."""
        if recipient not in self._agents:
            logger.error("Recipient %s not registered – message dropped", recipient)
            return
        msg = Message(
            sender=sender,
            recipient=recipient,
            timestamp=datetime.utcnow(),
            payload=payload,
        )
        self._agents[recipient].append(msg)
        logger.debug("Delivered %s", msg)

    def broadcast(self, sender: str, payload: str) -> None:
        """Send ``payload`` from ``sender`` to **all** registered agents."""
        timestamp = datetime.utcnow()
        for agent_id in self._agents:
            if agent_id == sender:
                continue  # optional: skip sender's own inbox
            msg = Message(
                sender=sender,
                recipient=agent_id,
                timestamp=timestamp,
                payload=payload,
            )
            self._agents[agent_id].append(msg)
        logger.info("Broadcast from %s to %d agents", sender, len(self._agents) - 1)

    # ------------------------------------------------------------------
    # Inbox handling
    # ------------------------------------------------------------------
    def receive_all(self, agent_id: str) -> List[Message]:
        """Return **and clear** all pending messages for ``agent_id``."""
        inbox = self._agents.get(agent_id, [])
        self._agents[agent_id] = []
        logger.debug("Agent %s retrieved %d messages", agent_id, len(inbox))
        return inbox

    def peek(self, agent_id: str) -> List[Message]:
        """Return a copy of the inbox without clearing it."""
        return list(self._agents.get(agent_id, []))

    # ------------------------------------------------------------------
    # Introspection helpers (useful for debugging or UI)
    # ------------------------------------------------------------------
    def list_agents(self) -> List[str]:
        """Return a list of currently registered agent identifiers."""
        return list(self._agents.keys())

    def inbox_size(self, agent_id: str) -> int:
        """Return the number of pending messages for ``agent_id``."""
        return len(self._agents.get(agent_id, []))


# End of CollaborationManager
