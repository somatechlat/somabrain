"""OpenTelemetry bootstrap helpers."""

from __future__ import annotations

import logging
from typing import Optional

try:  # pragma: no cover - optional dependency guard
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.trace import Tracer
except Exception as exc:  # pragma: no cover
    # Log the import failure for debugging purposes while keeping the optional nature.
    _LOG.exception("Failed to import OpenTelemetry modules: %s", exc)
    trace = None  # type: ignore
    Tracer = None  # type: ignore

_LOG = logging.getLogger(__name__)


def configure_tracing(
    service_name: str,
    collector_endpoint: str = "http://otel-collector.soma-infra.svc.cluster.local:4317",
) -> None:
    """Initialise OpenTelemetry tracing for a service."""

    if trace is None:  # pragma: no cover - executed when OTel missing
        _LOG.warning(
            "OpenTelemetry SDK not installed; tracing disabled for %s", service_name
        )
        return

    provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
    span_exporter = OTLPSpanExporter(endpoint=collector_endpoint, insecure=True)
    span_processor = BatchSpanProcessor(span_exporter)
    provider.add_span_processor(span_processor)
    trace.set_tracer_provider(provider)


def get_tracer(service_name: str) -> Optional[Tracer]:
    if trace is None:  # pragma: no cover - executed when OTel missing
        return None
    return trace.get_tracer(service_name)


__all__ = ["configure_tracing", "get_tracer"]
