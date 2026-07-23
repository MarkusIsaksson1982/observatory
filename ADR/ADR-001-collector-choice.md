# ADR-001: Collector Choice — Grafana Alloy

**Status:** Accepted
**Date:** 2026-07-19
**Deciders:** Technical Lead, Implementation Engineer

## Context

We need an OpenTelemetry collector to receive OTLP from instrumented services and forward to Mimir (metrics), Loki (logs), and Tempo (traces).

Options:
1. **Grafana Agent** — Legacy, EOL November 2025
2. **OpenTelemetry Collector (vanilla)** — Vendor-neutral, but requires manual pipeline config for each backend
3. **Grafana Alloy** — Grafana's strategic successor to Agent; native Mimir/Loki/Tempo integration; River config

## Decision

**Use Grafana Alloy.**

## Consequences

### Positive
- **Current:** Agent EOL Nov 2025; Alloy is Grafana's strategic direction
- **Native integration:** Purpose-built pipelines for Mimir/Loki/Tempo with minimal config
- **River config:** Declarative, type-safe, supports components and blocks
- **Single binary:** Metrics, logs, traces, profiles in one process
- **Portfolio signal:** Demonstrates "staying current with ecosystem" (job requirement)

### Negative
- **Newer:** Less community content than vanilla OTel Collector (mitigated: Grafana docs excellent)
- **River learning curve:** New config language (mitigated: simpler than YAML pipelines)

### Neutral
- Alloy is OTel Collector under the hood; OTel knowledge transfers

## Alternatives Considered

1. **Vanilla OTel Collector** — Rejected: manual pipeline config for each backend; no native Mimir/Loki/Tempo optimizations
2. **Grafana Agent** — Rejected: EOL Nov 2025; using it would contradict "stay current" claim

## References

- [Grafana Alloy Documentation](https://grafana.com/docs/alloy/)
- [Grafana Agent EOL Announcement](https://grafana.com/blog/2024/11/01/grafana-agent-end-of-life/)
- PROJECT_CONSTITUTION.md Section 3 (Technology Choices)