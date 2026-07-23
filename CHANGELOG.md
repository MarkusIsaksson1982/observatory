# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Loki service with TSDB schema, filesystem storage
- Alloy OTLP → Loki exporter wiring (`otelcol.exporter.loki`, `loki.write`)
- Gateway OTel instrumentation (FastAPI, httpx, logging)
- Gateway health endpoint (`/health`)
- Makefile targets (up, down, logs, validate)

### Fixed
- Alloy healthcheck (curl → bash TCP check — no curl/wget in grafana/alloy image)
- Loki healthcheck (wget spider — confirmed present in grafana/loki:3.1.0)
- Gateway Dockerfile CMD (removed redundant opentelemetry-instrument CLI)
- FastAPIInstrumentor instance method call (class → instance)

---

## [0.1.0] - 2026-07-19

### Added
- Repository initialized
- FastAPI gateway with OTel instrumentation
- Alloy with OTLP receiver
- Docker Compose with healthchecks for Gateway, Alloy
- Gateway Dockerfile (Python 3.13-slim)
- ADR-001: Collector Choice (Alloy over vanilla OTel Collector)
- ADR-003: Log Label Strategy
- ADR-009: Dashboard Provisioning Strategy
