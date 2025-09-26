"""Optional tracing tests.

These tests only run when the OpenTelemetry SDK is installed in the test
environment. They are guarded so CI without OTel SDK won't fail.
"""

import pytest

from observability import provider


@pytest.mark.skipif(
    not hasattr(provider, "OTEL_AVAILABLE") or not provider.OTEL_AVAILABLE,
    reason="OpenTelemetry SDK not installed",
)
def test_init_tracing_and_emit_span(monkeypatch):
    # This test requires opentelemetry sdk to be installed.
    # We configure an in-memory span exporter and assert that spans are created.
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import (
            InMemorySpanExporter,
            SimpleSpanProcessor,
        )
    except Exception:
        pytest.skip("OTel SDK import failed")

    exporter = InMemorySpanExporter()
    tp = TracerProvider()
    tp.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(tp)

    # initialize provider (should be idempotent)
    provider.init_tracing()
    tracer = provider.get_tracer("tests.optional")

    with tracer.start_as_current_span("test.span") as span:
        span.set_attribute("test.attr", "ok")

    spans = exporter.get_finished_spans()
    assert any(s.name == "test.span" for s in spans)
