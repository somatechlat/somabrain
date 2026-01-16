"""Transaction Event Store for SomaBrain - Django ORM version.

Provides durable event sourcing via Kafka with PostgreSQL fallback.
Every transaction is stored as an immutable event for full audit trail.

Architecture:
    ┌─────────────────┐     ┌─────────────────┐
    │  Transaction    │────▶│  Kafka Topic    │
    │    Event        │     │  txn.events     │
    └─────────────────┘     └─────────────────┘
            │                       │
            ▼                       ▼
    ┌─────────────────┐     ┌─────────────────┐
    │  PostgreSQL     │     │  Event Replay   │
    │  (canonical)    │     │  Consumer       │
    └─────────────────┘     └─────────────────┘

VIBE Compliance:
    - Real Kafka producer (no mocks)
    - Real PostgreSQL storage via Django ORM (no mocks)
    - Full audit trail with correlation IDs

Migrated from SQLAlchemy to Django ORM.
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from django.conf import settings

logger = logging.getLogger(__name__)


class TransactionStatus(str, Enum):
    """Transaction lifecycle states."""

    PENDING = "pending"
    COMMITTED = "committed"
    ROLLED_BACK = "rolled_back"
    COMPENSATING = "compensating"
    FAILED = "failed"


class TransactionType(str, Enum):
    """Types of transactions in the system."""

    MEMORY_STORE = "memory.store"
    MEMORY_RECALL = "memory.recall"
    MEMORY_DELETE = "memory.delete"
    SLEEP_TRANSITION = "sleep.transition"
    NEUROMOD_UPDATE = "neuromod.update"
    ADAPTATION_UPDATE = "adaptation.update"
    PERSONA_CREATE = "persona.create"
    PERSONA_UPDATE = "persona.update"
    PERSONA_DELETE = "persona.delete"
    CONTEXT_EVALUATE = "context.evaluate"
    PLAN_SUGGEST = "plan.suggest"
    CUSTOM = "custom"


@dataclass
class TransactionEvent:
    """Immutable transaction event for event sourcing.

    Every operation in SomaBrain produces a TransactionEvent that is:
    - Stored in Kafka for replay capability
    - Stored in PostgreSQL for querying
    - Linked via trace_id for distributed tracing
    """

    # Identity
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: Optional[str] = None
    parent_event_id: Optional[str] = None

    # Transaction metadata
    transaction_type: TransactionType = TransactionType.CUSTOM
    status: TransactionStatus = TransactionStatus.PENDING

    # Context
    tenant_id: Optional[str] = None
    persona_id: Optional[str] = None
    session_id: Optional[str] = None

    # Payload
    operation: str = ""
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)

    # Compensation
    compensating_action: Optional[str] = None
    compensation_data: Dict[str, Any] = field(default_factory=dict)

    # Timing
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    duration_ms: Optional[float] = None

    # Error handling
    error: Optional[str] = None
    error_code: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3

    # Metadata
    version: str = "1.0"
    source_service: str = "somabrain"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize event to dictionary."""
        data = asdict(self)
        data["transaction_type"] = self.transaction_type.value
        data["status"] = self.status.value
        data["created_at"] = self.created_at.isoformat()
        if self.completed_at:
            data["completed_at"] = self.completed_at.isoformat()
        return data

    def to_json(self) -> str:
        """Serialize event to JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False, default=str)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TransactionEvent:
        """Deserialize event from dictionary."""
        # Handle enum conversion
        if "transaction_type" in data:
            data["transaction_type"] = TransactionType(data["transaction_type"])
        if "status" in data:
            data["status"] = TransactionStatus(data["status"])

        # Handle datetime conversion
        if "created_at" in data and isinstance(data["created_at"], str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if "completed_at" in data and isinstance(data["completed_at"], str):
            data["completed_at"] = datetime.fromisoformat(data["completed_at"])

        return cls(**data)

    def mark_committed(self, output_data: Optional[Dict[str, Any]] = None) -> None:
        """Mark transaction as successfully committed."""
        self.status = TransactionStatus.COMMITTED
        self.completed_at = datetime.now(timezone.utc)
        if output_data:
            self.output_data = output_data
        if self.created_at:
            self.duration_ms = (self.completed_at - self.created_at).total_seconds() * 1000

    def mark_failed(self, error: str, error_code: Optional[str] = None) -> None:
        """Mark transaction as failed."""
        self.status = TransactionStatus.FAILED
        self.completed_at = datetime.now(timezone.utc)
        self.error = error
        self.error_code = error_code
        if self.created_at:
            self.duration_ms = (self.completed_at - self.created_at).total_seconds() * 1000

    def mark_rolled_back(self) -> None:
        """Mark transaction as rolled back via compensation."""
        self.status = TransactionStatus.ROLLED_BACK
        self.completed_at = datetime.now(timezone.utc)
        if self.created_at:
            self.duration_ms = (self.completed_at - self.created_at).total_seconds() * 1000


# Kafka topic definitions for transactions
TRANSACTION_TOPICS = {
    "events": "txn.events",  # All transaction events
    "replay": "txn.replay",  # Replay requests
    "compensate": "txn.compensate",  # Compensation requests
    "dlq": "txn.dlq",  # Dead letter queue
}


class TransactionEventStore:
    """Event store for transaction event sourcing.

    Provides:
    - Kafka-based event streaming for replay
    - PostgreSQL storage for querying via Django ORM
    - Full audit trail with correlation

    VIBE Compliance:
        - Real Kafka producer (confluent-kafka)
        - Real PostgreSQL via Django ORM
        - No mocks, no stubs
    """

    def __init__(self) -> None:
        """Initialize the instance."""

        self._producer = None
        self._initialized = False
        self._event_handlers: List[Callable[[TransactionEvent], None]] = []

    def _ensure_producer(self) -> None:
        """Lazily initialize Kafka producer."""
        if self._producer is not None:
            return

        try:
            from confluent_kafka import Producer

            bootstrap = getattr(settings, "KAFKA_BOOTSTRAP_SERVERS", "")
            if not bootstrap:
                bootstrap = getattr(settings, "KAFKA_BOOTSTRAP", "")

            if not bootstrap:
                logger.warning("Kafka bootstrap servers not configured, events will be logged only")
                return

            bootstrap = bootstrap.replace("kafka://", "")

            self._producer = Producer(
                {
                    "bootstrap.servers": bootstrap,
                    "enable.idempotence": True,
                    "acks": "all",
                    "compression.type": "snappy",
                    "client.id": f"somabrain-txn-{uuid.uuid4().hex[:8]}",
                }
            )
            self._initialized = True
            logger.info("🔗 Transaction event store connected to Kafka")

        except Exception as e:
            logger.warning(f"Failed to initialize Kafka producer: {e}")

    def append(self, event: TransactionEvent) -> bool:
        """Append a transaction event to the store.

        Events are:
        1. Published to Kafka for streaming/replay
        2. Stored in PostgreSQL for querying
        3. Dispatched to registered handlers

        Args:
            event: The transaction event to store

        Returns:
            True if event was successfully stored
        """
        self._ensure_producer()

        success = True

        # Publish to Kafka
        if self._producer:
            try:
                topic = TRANSACTION_TOPICS["events"]
                key = f"{event.tenant_id or 'default'}:{event.trace_id}"

                self._producer.produce(
                    topic,
                    key=key.encode("utf-8"),
                    value=event.to_json().encode("utf-8"),
                    headers=[
                        ("trace-id", event.trace_id.encode("utf-8")),
                        ("event-type", event.transaction_type.value.encode("utf-8")),
                        ("status", event.status.value.encode("utf-8")),
                    ],
                )
                self._producer.poll(0)  # Trigger delivery callbacks

            except Exception as e:
                logger.error(f"Failed to publish transaction event to Kafka: {e}")
                success = False

        # Store in PostgreSQL via outbox pattern
        try:
            self._store_to_outbox(event)
        except Exception as e:
            logger.error(f"Failed to store transaction event to outbox: {e}")
            success = False

        # Dispatch to handlers
        for handler in self._event_handlers:
            try:
                handler(event)
            except Exception as e:
                logger.warning(f"Event handler failed: {e}")

        return success

    def _store_to_outbox(self, event: TransactionEvent) -> None:
        """Store event to PostgreSQL outbox for durability using Django ORM."""
        try:
            from somabrain.models import OutboxEvent

            OutboxEvent.objects.create(
                topic=TRANSACTION_TOPICS["events"],
                payload=event.to_dict(),
                tenant_id=event.tenant_id or "default",
                dedupe_key=event.event_id,
                status="pending",
            )

        except ImportError:
            # Outbox not available, log only
            logger.debug("Outbox not available, event logged only")
        except Exception as e:
            logger.warning(f"Failed to store to outbox: {e}")

    def query(
        self,
        trace_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        transaction_type: Optional[TransactionType] = None,
        status: Optional[TransactionStatus] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[TransactionEvent]:
        """Query transaction events from PostgreSQL using Django ORM.

        Args:
            trace_id: Filter by trace ID
            tenant_id: Filter by tenant
            transaction_type: Filter by transaction type
            status: Filter by status
            since: Filter events after this time
            until: Filter events before this time
            limit: Maximum events to return

        Returns:
            List of matching transaction events
        """
        # Query from PostgreSQL outbox using Django ORM
        try:
            from somabrain.models import OutboxEvent

            qs = OutboxEvent.objects.filter(topic=TRANSACTION_TOPICS["events"])

            if tenant_id:
                qs = qs.filter(tenant_id=tenant_id)

            qs = qs.order_by("-created_at")[:limit]

            events = []
            for row in qs:
                try:
                    event = TransactionEvent.from_dict(row.payload)

                    # Apply additional filters
                    if trace_id and event.trace_id != trace_id:
                        continue
                    if transaction_type and event.transaction_type != transaction_type:
                        continue
                    if status and event.status != status:
                        continue
                    if since and event.created_at < since:
                        continue
                    if until and event.created_at > until:
                        continue

                    events.append(event)
                except Exception as e:
                    logger.warning(f"Failed to parse event: {e}")

            return events

        except Exception as e:
            logger.error(f"Failed to query events: {e}")
            return []

    def replay(
        self,
        trace_id: str,
        handler: Callable[[TransactionEvent], None],
    ) -> int:
        """Replay all events for a trace ID.

        Args:
            trace_id: The trace ID to replay
            handler: Callback for each event

        Returns:
            Number of events replayed
        """
        events = self.query(trace_id=trace_id, limit=1000)
        events.sort(key=lambda e: e.created_at)

        for event in events:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Replay handler failed for event {event.event_id}: {e}")

        return len(events)

    def request_compensation(self, event: TransactionEvent) -> bool:
        """Request compensation for a failed transaction.

        Publishes to the compensation topic for async processing.

        Args:
            event: The event to compensate

        Returns:
            True if compensation request was published
        """
        self._ensure_producer()

        if not self._producer:
            logger.error("Cannot request compensation: Kafka not available")
            return False

        if not event.compensating_action:
            logger.warning(f"No compensating action defined for event {event.event_id}")
            return False

        try:
            event.status = TransactionStatus.COMPENSATING

            self._producer.produce(
                TRANSACTION_TOPICS["compensate"],
                key=event.trace_id.encode("utf-8"),
                value=event.to_json().encode("utf-8"),
                headers=[
                    ("trace-id", event.trace_id.encode("utf-8")),
                    ("action", event.compensating_action.encode("utf-8")),
                ],
            )
            self._producer.flush(timeout=5)

            logger.info(f"🔄 Compensation requested for event {event.event_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to request compensation: {e}")
            return False

    def register_handler(self, handler: Callable[[TransactionEvent], None]) -> None:
        """Register an event handler for real-time processing."""
        self._event_handlers.append(handler)

    def flush(self, timeout: float = 5.0) -> None:
        """Flush pending events to Kafka."""
        if self._producer:
            self._producer.flush(timeout)

    def close(self) -> None:
        """Close the event store and cleanup resources."""
        if self._producer:
            try:
                self._producer.flush(5)
            except Exception:
                pass
            self._producer = None
        self._initialized = False


# ---------------------------------------------------------------------------
# DI Container Integration
# ---------------------------------------------------------------------------


def _create_event_store() -> TransactionEventStore:
    """Factory function for DI container."""
    return TransactionEventStore()


def get_event_store() -> TransactionEventStore:
    """Get the event store instance from DI container.

    VIBE Compliance:
        - Uses DI container for singleton management
        - Thread-safe lazy instantiation
    """
    from somabrain.core.container import container

    if not container.has("transaction_event_store"):
        container.register("transaction_event_store", _create_event_store)
    return container.get("transaction_event_store")
