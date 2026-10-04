"""OpenTelemetry bootstrap helpers."""

from __future__ import annotations

import logging

_LOG = logging.getLogger(__name__)

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
    trace = None
    Tracer = None


def configure_tracing(
    service_name: str,
    collector_endpoint: str | None = None,
) -> None:
    """Initialise OpenTelemetry tracing for a service.

    ``collector_endpoint`` is deployment topology. When omitted it is resolved
    from ``OTEL_EXPORTER_OTLP_ENDPOINT``; a missing setting raises. There is no
    cluster DNS name or localhost fallback at the call site (Rule 91).
    """

    if trace is None:  # pragma: no cover - executed when OTel missing
        _LOG.warning(
            "OpenTelemetry SDK not installed; tracing disabled for %s", service_name
        )
        return

    from somabrain.settings.resolve import require_url

    endpoint = (
        require_url("OTEL_EXPORTER_OTLP_ENDPOINT")
        if collector_endpoint is None
        else str(collector_endpoint).strip()
    )
    if "://" not in endpoint:
        raise ValueError(
            "collector_endpoint must be a URL with a scheme; protocol constants "
            "live in somabrain.settings.constants and the effective base is "
            "OTEL_EXPORTER_OTLP_ENDPOINT."
        )

    provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
    span_exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
    span_processor = BatchSpanProcessor(span_exporter)
    provider.add_span_processor(span_processor)
    trace.set_tracer_provider(provider)


def get_tracer(service_name: str) -> Tracer | None:
    """Retrieve tracer.

    Args:
        service_name: The service_name.
    """

    if trace is None:  # pragma: no cover - executed when OTel missing
        return None
    return trace.get_tracer(service_name)


__all__ = ["configure_tracing", "get_tracer"]
