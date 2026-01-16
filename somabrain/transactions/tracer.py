"""Transaction Tracer for SomaBrain.

Provides distributed tracing and correlation for all transactions.
Every operation gets a trace_id that follows it through the entire system.

Usage:
    from somabrain.transactions import trace_transaction, get_tracer

    # Decorator usage
    @trace_transaction(TransactionType.MEMORY_STORE)
    async def store_memory(coord, payload):
        ...

    # Context manager usage
    tracer = get_tracer()
    with tracer.span("memory.store") as span:
        span.set_attribute("coordinate", coord)
        ...

VIBE Compliance:
    - Real OpenTelemetry integration
    - Real correlation IDs
    - Full audit trail
"""

from __future__ import annotations

import functools
import logging
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Generator, Optional, TypeVar

from somabrain.transactions.event_store import (
    TransactionEvent,
    TransactionType,
    get_event_store,
)

logger = logging.getLogger(__name__)

# Context variables for trace propagation
_current_trace_id: ContextVar[Optional[str]] = ContextVar("trace_id", default=None)
_current_span_id: ContextVar[Optional[str]] = ContextVar("span_id", default=None)
_current_tenant_id: ContextVar[Optional[str]] = ContextVar("tenant_id", default=None)
_current_persona_id: ContextVar[Optional[str]] = ContextVar("persona_id", default=None)

T = TypeVar("T")


@dataclass
class Span:
    """A span represents a single operation within a trace.

    Spans can be nested to represent hierarchical operations.
    """

    span_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    trace_id: str = ""
    parent_span_id: Optional[str] = None
    operation: str = ""

    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None

    attributes: Dict[str, Any] = field(default_factory=dict)
    events: list = field(default_factory=list)
    status: str = "ok"
    error: Optional[str] = None

    def set_attribute(self, key: str, value: Any) -> None:
        """Set a span attribute."""
        self.attributes[key] = value

    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
        """Add an event to the span."""
        self.events.append(
            {
                "name": name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "attributes": attributes or {},
            }
        )

    def set_error(self, error: str) -> None:
        """Mark span as errored."""
        self.status = "error"
        self.error = error

    def finish(self) -> None:
        """Finish the span and calculate duration."""
        self.end_time = datetime.now(timezone.utc)
        self.duration_ms = (self.end_time - self.start_time).total_seconds() * 1000


class TransactionTracer:
    """Distributed transaction tracer for SomaBrain.

    Provides:
    - Trace ID propagation across services
    - Span creation and nesting
    - Automatic event store integration
    - OpenTelemetry compatibility

    VIBE Compliance:
        - Real tracing (no mocks)
        - Full correlation chain
        - Kafka event publishing
    """

    def __init__(self) -> None:
        """Initialize the instance."""

        self._otel_tracer = None
        self._initialized = False
        self._try_init_otel()

    def _try_init_otel(self) -> None:
        """Try to initialize OpenTelemetry tracer."""
        try:
            from opentelemetry import trace
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.resources import Resource

            # Check if already configured
            if trace.get_tracer_provider().__class__.__name__ != "ProxyTracerProvider":
                self._otel_tracer = trace.get_tracer("somabrain.transactions")
                self._initialized = True
                logger.info("🔍 Transaction tracer connected to OpenTelemetry")
                return

            # Configure basic tracer
            resource = Resource.create({"service.name": "somabrain"})
            provider = TracerProvider(resource=resource)
            trace.set_tracer_provider(provider)
            self._otel_tracer = trace.get_tracer("somabrain.transactions")
            self._initialized = True

        except ImportError:
            logger.debug("OpenTelemetry not available, using basic tracing")
        except Exception as e:
            logger.warning(f"Failed to initialize OpenTelemetry: {e}")

    def new_trace_id(self) -> str:
        """Generate a new trace ID."""
        return str(uuid.uuid4())

    def get_current_trace_id(self) -> Optional[str]:
        """Get the current trace ID from context."""
        return _current_trace_id.get()

    def set_current_trace_id(self, trace_id: str) -> None:
        """Set the current trace ID in context."""
        _current_trace_id.set(trace_id)

    def get_current_tenant_id(self) -> Optional[str]:
        """Get the current tenant ID from context."""
        return _current_tenant_id.get()

    def set_current_tenant_id(self, tenant_id: str) -> None:
        """Set the current tenant ID in context."""
        _current_tenant_id.set(tenant_id)

    def get_current_persona_id(self) -> Optional[str]:
        """Get the current persona ID from context."""
        return _current_persona_id.get()

    def set_current_persona_id(self, persona_id: str) -> None:
        """Set the current persona ID in context."""
        _current_persona_id.set(persona_id)

    @contextmanager
    def span(
        self,
        operation: str,
        transaction_type: TransactionType = TransactionType.CUSTOM,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> Generator[Span, None, None]:
        """Create a traced span for an operation.

        Args:
            operation: Name of the operation
            transaction_type: Type of transaction
            attributes: Initial span attributes

        Yields:
            Span object for adding attributes and events
        """
        # Get or create trace ID
        trace_id = _current_trace_id.get()
        if not trace_id:
            trace_id = self.new_trace_id()
            _current_trace_id.set(trace_id)

        # Get parent span
        parent_span_id = _current_span_id.get()

        # Create span
        span = Span(
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            operation=operation,
        )

        if attributes:
            span.attributes.update(attributes)

        # Set as current span
        token = _current_span_id.set(span.span_id)

        # Create transaction event
        event = TransactionEvent(
            trace_id=trace_id,
            correlation_id=parent_span_id,
            transaction_type=transaction_type,
            operation=operation,
            tenant_id=_current_tenant_id.get(),
            persona_id=_current_persona_id.get(),
            input_data=attributes or {},
        )

        try:
            # OpenTelemetry span if available
            otel_span = None
            if self._otel_tracer:
                otel_span = self._otel_tracer.start_span(operation)
                if attributes:
                    for k, v in attributes.items():
                        otel_span.set_attribute(k, str(v))

            yield span

            # Success
            span.finish()
            event.mark_committed(output_data=span.attributes)

            if otel_span:
                otel_span.end()

        except Exception as e:
            # Error
            span.set_error(str(e))
            span.finish()
            event.mark_failed(str(e))

            if otel_span:
                otel_span.record_exception(e)
                otel_span.end()

            raise

        finally:
            # Restore parent span
            _current_span_id.reset(token)

            # Store event
            try:
                event_store = get_event_store()
                event_store.append(event)
            except Exception as store_error:
                logger.warning(f"Failed to store transaction event: {store_error}")

    def trace_context(
        self,
        trace_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        persona_id: Optional[str] = None,
    ):
        """Context manager to set trace context.

        Args:
            trace_id: Trace ID to use (generates new if None)
            tenant_id: Tenant ID for the context
            persona_id: Persona ID for the context
        """

        @contextmanager
        def _context():
            # Save current values
            """Execute context."""

            old_trace = _current_trace_id.get()
            old_tenant = _current_tenant_id.get()
            old_persona = _current_persona_id.get()

            # Set new values
            _current_trace_id.set(trace_id or self.new_trace_id())
            if tenant_id:
                _current_tenant_id.set(tenant_id)
            if persona_id:
                _current_persona_id.set(persona_id)

            try:
                yield
            finally:
                # Restore old values
                _current_trace_id.set(old_trace)
                _current_tenant_id.set(old_tenant)
                _current_persona_id.set(old_persona)

        return _context()

    def extract_context(self, headers: Dict[str, str]) -> Dict[str, Optional[str]]:
        """Extract trace context from HTTP headers.

        Args:
            headers: HTTP headers dict

        Returns:
            Dict with trace_id, tenant_id, persona_id
        """
        return {
            "trace_id": headers.get("x-trace-id") or headers.get("traceparent"),
            "tenant_id": headers.get("x-tenant-id"),
            "persona_id": headers.get("x-persona-id"),
        }

    def inject_context(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Inject trace context into HTTP headers.

        Args:
            headers: HTTP headers dict to modify

        Returns:
            Modified headers dict
        """
        trace_id = _current_trace_id.get()
        if trace_id:
            headers["x-trace-id"] = trace_id

        tenant_id = _current_tenant_id.get()
        if tenant_id:
            headers["x-tenant-id"] = tenant_id

        persona_id = _current_persona_id.get()
        if persona_id:
            headers["x-persona-id"] = persona_id

        return headers


def trace_transaction(
    transaction_type: TransactionType = TransactionType.CUSTOM,
    operation: Optional[str] = None,
    capture_args: bool = True,
    capture_result: bool = True,
):
    """Decorator to trace a function as a transaction.

    Args:
        transaction_type: Type of transaction
        operation: Operation name (defaults to function name)
        capture_args: Whether to capture function arguments
        capture_result: Whether to capture return value

    Usage:
        @trace_transaction(TransactionType.MEMORY_STORE)
        async def store_memory(coord, payload):
            ...
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        """Execute decorator.

        Args:
            func: The func.
        """

        op_name = operation or f"{func.__module__}.{func.__name__}"

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> T:
            """Execute sync wrapper."""

            tracer = get_tracer()

            # Build attributes from args
            attributes = {}
            if capture_args:
                # Capture kwargs
                for k, v in kwargs.items():
                    if _is_serializable(v):
                        attributes[f"arg.{k}"] = v

            with tracer.span(op_name, transaction_type, attributes) as span:
                result = func(*args, **kwargs)

                if capture_result and _is_serializable(result):
                    span.set_attribute("result", result)

                return result

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> T:  # type: ignore[misc]
            """Execute async wrapper."""

            tracer = get_tracer()

            # Build attributes from args
            attributes = {}
            if capture_args:
                for k, v in kwargs.items():
                    if _is_serializable(v):
                        attributes[f"arg.{k}"] = v

            with tracer.span(op_name, transaction_type, attributes) as span:
                result = await func(*args, **kwargs)

                if capture_result and _is_serializable(result):
                    span.set_attribute("result", result)

                return result

        # Return appropriate wrapper
        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore[return-value]
        return sync_wrapper  # type: ignore[return-value]

    return decorator


def _is_serializable(value: Any) -> bool:
    """Check if a value is JSON-serializable."""
    if value is None:
        return True
    if isinstance(value, (str, int, float, bool)):
        return True
    if isinstance(value, (list, tuple)):
        return all(_is_serializable(v) for v in value)
    if isinstance(value, dict):
        return all(isinstance(k, str) and _is_serializable(v) for k, v in value.items())
    return False


# ---------------------------------------------------------------------------
# DI Container Integration
# ---------------------------------------------------------------------------


def _create_tracer() -> TransactionTracer:
    """Factory function for DI container."""
    return TransactionTracer()


def get_tracer() -> TransactionTracer:
    """Get the tracer instance from DI container.

    VIBE Compliance:
        - Uses DI container for singleton management
        - Thread-safe lazy instantiation
    """
    from somabrain.core.container import container

    if not container.has("transaction_tracer"):
        container.register("transaction_tracer", _create_tracer)
    return container.get("transaction_tracer")
