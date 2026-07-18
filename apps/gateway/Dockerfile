# Multi-stage Dockerfile for Gateway Service
# Optimized for size and security

# Build stage
FROM python:3.12-slim@sha256:8b89c0d8c3e8f3e8b8c5e8f8b8c5e8f8b8c5e8f8b8c5e8f8b8c5e8f8b8c5e8f8 AS builder

# Install uv for fast dependency installation
RUN pip install --no-cache-dir uv

WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock* ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Runtime stage
FROM python:3.12-slim@sha256:8b89c0d8c3e8f3e8b8c5e8f8b8c5e8f8b8c5e8f8b8c5e8f8b8c5e8f8b8c5e8f8 AS runtime

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY . .

# Set PATH to use virtual environment
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Switch to non-root user
USER appuser

EXPOSE 8000

# Run with OpenTelemetry auto-instrumentation
CMD ["python", "-m", "opentelemetry-instrument", "main.py"]