"""
OpenTelemetry Instrumentation for Gateway Service.

Configures:
- Auto-instrumentation (FastAPI, httpx, logging)
- Manual instrumentation for business spans
- Structured JSON logging with traceID injection
- OTLP log export to Alloy → Loki
- Exemplars on histogram metrics
"""

import logging
import os

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, SERVICE_VERSION, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from pythonjsonlogger import jsonlogger

try:
    from opentelemetry._logs import set_logger_provider
    from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
    from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
    from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
except ImportError:
    from opentelemetry.exporter.otlp.proto.grpc.log_exporter import OTLPLogExporter
    from opentelemetry.logs import set_logger_provider
    from opentelemetry.sdk.logs import LoggerProvider, LoggingHandler
    from opentelemetry.sdk.logs.export import BatchLogRecordProcessor


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

    # Structured logging with traceID injection + OTLP log export
    setup_structured_logging(resource=resource, otlp_endpoint=otlp_endpoint)

    return tracer


def setup_structured_logging(resource: Resource, otlp_endpoint: str) -> None:
    """
    Configure JSON logging with traceID injection and OTLP log export.

    Two output paths:
      1. stdout JSON — human-readable, includes traceID field
      2. OTLP to Alloy — structured log records with automatic trace context,
         flowing through loki_hints processor → Loki
    """

    class TraceIDFilter(logging.Filter):
        """Inject current traceID and spanID into log records."""
        def filter(self, record: logging.LogRecord) -> bool:
            span = trace.get_current_span()
            if span and span.get_span_context().trace_id:
                record.traceID = format(span.get_span_context().trace_id, '032x')
                record.spanID = format(span.get_span_context().span_id, '016x')
            else:
                record.traceID = "00000000000000000000000000000000"
                record.spanID = "0000000000000000"
            return True

    # JSON formatter with traceID/spanID
    class JSONFormatter(jsonlogger.JsonFormatter):
        def add_fields(self, log_record, record, message_dict):
            super().add_fields(log_record, record, message_dict)
            log_record['timestamp'] = record.created
            log_record['level'] = record.levelname
            log_record['logger'] = record.name
            if hasattr(record, 'traceID'):
                log_record['traceID'] = record.traceID
            if hasattr(record, 'spanID'):
                log_record['spanID'] = record.spanID

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # 1) Stdout JSON handler — human-readable logs
    stdout_handler = logging.StreamHandler()
    stdout_handler.setFormatter(JSONFormatter())
    stdout_handler.addFilter(TraceIDFilter())
    root_logger.addHandler(stdout_handler)

    # 2) OTLP log export to Alloy → Loki
    logger_provider = LoggerProvider(resource=resource)
    log_exporter = OTLPLogExporter(
        endpoint=otlp_endpoint,
        insecure=True,
    )
    logger_provider.add_log_record_processor(
        BatchLogRecordProcessor(log_exporter)
    )
    set_logger_provider(logger_provider)

    otlp_handler = LoggingHandler(
        level=logging.NOTSET,
        logger_provider=logger_provider,
    )
    root_logger.addHandler(otlp_handler)

    # Inject trace context into standard logging records.
    # set_logging_format=False: we handle formatting ourselves via JSONFormatter.
    LoggingInstrumentor().instrument(set_logging_format=False)


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
            "db.query",
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


# Fibonacci workload for trace generation
# NOTE: Deliberately sync — @tracer.start_as_current_span as decorator
# does not work correctly on async functions (opentelemetry-python#3270).
# CPU-bound math has no business being async anyway.
@tracer.start_as_current_span("fibonacci")
def compute_fibonacci(n: int) -> int:
    span = trace.get_current_span()
    span.set_attribute("fib.n", n)
    span.set_attribute("fib.algorithm", "iterative")
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    span.set_attribute("fib.result", a)
    return a
