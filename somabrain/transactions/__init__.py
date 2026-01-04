"""Transaction Event Sourcing System for SomaBrain.

Provides:
- Full audit trail with correlation IDs
- Reversible transactions via compensating actions
- Replayable events via Kafka event sourcing
- Beautiful human-readable logging

Per SRS Requirements:
- Every operation is traceable (trace_id, correlation_id)
- Every operation is reversible (compensating transactions)
- Every operation is replayable (Kafka event log)
"""

from somabrain.transactions.event_store import (
    TransactionEvent,
    TransactionEventStore,
    get_event_store,
)
from somabrain.transactions.tracer import (
    TransactionTracer,
    get_tracer,
    trace_transaction,
)
from somabrain.transactions.compensator import (
    CompensatingAction,
    TransactionCompensator,
    get_compensator,
)

__all__ = [
    "TransactionEvent",
    "TransactionEventStore",
    "get_event_store",
    "TransactionTracer",
    "get_tracer",
    "trace_transaction",
    "CompensatingAction",
    "TransactionCompensator",
    "get_compensator",
]