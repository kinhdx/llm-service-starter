"""OpenTelemetry setup: traces go to an OTLP collector when OTEL_EXPORTER_OTLP_ENDPOINT is set, otherwise to
stdout as JSON lines. FastAPI requests and model calls end up in the same trace."""
from __future__ import annotations

import os

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter, SimpleSpanProcessor

_configured = False


def setup(service_name: str) -> None:
    global _configured
    if _configured:
        return
    provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
    if os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"):
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    elif os.getenv("OTEL_CONSOLE", "1") == "1":
        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter(
            formatter=lambda span: span.to_json(indent=None) + "\n")))
    trace.set_tracer_provider(provider)
    _configured = True
