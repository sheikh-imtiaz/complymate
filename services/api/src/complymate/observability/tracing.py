"""OpenTelemetry tracing. OTLP exporter → ADOT collector (CloudWatch/X-Ray) or Azure Monitor. Same code."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from complymate.config import Settings

_configured = False


def configure_tracing(settings: Settings, app: Any | None = None) -> None:
    global _configured
    if _configured:
        return
    provider = TracerProvider(
        resource=Resource.create(
            {
                "service.name": settings.service_name,
                "deployment.environment": settings.environment,
                "cloud.provider": settings.cloud_provider,
            }
        )
    )
    if settings.otel_exporter_otlp_endpoint:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint)))
    trace.set_tracer_provider(provider)
    if app is not None:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor.instrument_app(app, excluded_urls="health")
    _configured = True


tracer = trace.get_tracer("complymate")


@contextmanager
def agent_span(name: str, **attributes: Any) -> Iterator[trace.Span]:
    """Span for an agent tool call or model call. Callers add token counts and cost when known."""
    with tracer.start_as_current_span(f"agent.{name}") as span:
        for key, value in attributes.items():
            if value is not None:
                span.set_attribute(f"complymate.{key}", value)
        yield span
