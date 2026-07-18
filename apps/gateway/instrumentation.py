"""
OpenTelemetry Instrumentation for Gateway Service.

Configures:
- Auto-instrumentation (FastAPI, httpx, logging)
- Manual instrumentation for business spans
- Structured JSON logging with traceID injection
- Exemplars on histogram metrics
"""

import logging
import os
from typing import Optional

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from pythonjsonlogger import jsonlogger


def setup_telemetry() -> trace.Tracer:
    """
    Initialize OpenTelemetry SDK with OTLP exporter to Alloy.
    
    Returns:
        Configured tracer for manual instrumentation.
    """
    service_name = os.getenv("OTEL_SERVICE_NAME", "gateway")
    service_version = os.getenv("OTEL_SERVICE_VERSION", "0.1.0")
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://alloy:4317")
    
    # Create resource with service metadata
    resource = Resource.create({
        SERVICE_NAME: service_name,
        SERVICE_VERSION: service_version,
        "deployment.environment": os.getenv("ENVIRONMENT", "local"),
    })
    
    # Create tracer provider
    provider = TracerProvider(resource=resource)
    
    # Configure OTLP exporter to Alloy
    otlp_exporter = OTLPSpanExporter(
        endpoint=otlp_endpoint,
        insecure=True,
    )
    
    # Batch span processor for efficiency
    provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
    
    # Set as global tracer provider
    trace.set_tracer_provider(provider)
    
    # Get tracer for manual instrumentation
    tracer = trace.get_tracer(service_name, service_version)
    
    # Auto-instrumentation
    FastAPIInstrumentor.instrument()
    HTTPXClientInstrumentor.instrument()
    
    # Structured logging with traceID injection
    setup_structured_logging()
    
    return tracer


def setup_structured_logging() -> None:
    """
    Configure JSON logging with traceID injection.
    
    Adds traceID to every log record via LoggingInstrumentor
    and custom JSON formatter.
    """
    class TraceIDFilter(logging.Filter):
        """Inject current traceID into log records."""
        def filter(self, record: logging.LogRecord) -> bool:
            span = trace.get_current_span()
            if span and span.get_span_context().trace_id:
                record.traceID = format(span.get_span_context().trace_id, '032x')
            else:
                record.traceID = "none"
            return True
    
    # JSON formatter with traceID
    class JSONFormatter(jsonlogger.JsonFormatter):
        def add_fields(self, log_record, record, message_dict):
            super().add_fields(log_record, record, message_dict)
            log_record['timestamp'] = record.created
            log_record['level'] = record.levelname
            log_record['logger'] = record.name
            if hasattr(record, 'traceID'):
                log_record['traceID'] = record.traceID
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add JSON handler with traceID filter
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter(
        '%(timestamp)s %(level)s %(name)s %(message)s traceID=%(traceID)s'
    ))
    handler.addFilter(TraceIDFilter())
    root_logger.addHandler(handler)
    
    # Also instrument standard logging to include trace context
    LoggingInstrumentor().instrument(set_logging_format=True)


def get_tracer() -> trace.Tracer:
    """Get the configured tracer for manual instrumentation."""
    return trace.get_tracer("gateway", "0.1.0")


# Manual span helpers for business logic
class BusinessSpans:
    """Helper class for common business span patterns."""
    
    def __init__(self, tracer: trace.Tracer):
        self.tracer = tracer
    
    def http_call(self, method: str, url: str, service: str) -> trace.Span:
        """Create span for outbound HTTP call with standard attributes."""
        return self.tracer.start_span(
            f"http.client.{method.lower()}",
            kind=trace.SpanKind.CLIENT,
            attributes={
                "http.method": method,
                "http.url": url,
                "service.name": service,
            }
        )
    
    def business_operation(self, operation: str, **attributes) -> trace.Span:
        """Create span for business operation."""
        return self.tracer.start_span(
            f"business.{operation}",
            kind=trace.SpanKind.INTERNAL,
            attributes=attributes
        )
    
    def database_query(self, query: str, table: str) -> trace.Span:
        """Create span for database query."""
        return self.tracer.start_span(
            f"db.query",
            kind=trace.SpanKind.CLIENT,
            attributes={
                "db.statement": query[:200],  # Truncate long queries
                "db.table": table,
                "db.system": "postgresql",
            }
        )


# Exemplar helper for histograms
def record_with_exemplar(histogram, value: float, attributes: dict = None) -> None:
    """
    Record a value with current trace as exemplar.
    
    Args:
        histogram: OpenTelemetry Histogram instrument
        value: Value to record
        attributes: Additional attributes for the exemplar
    """
    span = trace.get_current_span()
    if span and span.get_span_context().trace_id:
        exemplar_attributes = attributes or {}
        exemplar_attributes.update({
            "traceID": format(span.get_span_context().trace_id, '032x'),
        })
        histogram.record(value, attributes=exemplar_attributes)
    else:
        histogram.record(value, attributes=attributes or {})


# Initialize on module import
tracer = setup_telemetry()
business_spans = BusinessSpans(tracer)