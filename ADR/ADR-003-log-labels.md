# ADR-003: Log Label Strategy — Low Cardinality, traceID as Label

**Status:** Accepted (updated 2026-07-19 with actual label naming)
**Date:** 2026-07-19
**Deciders:** Technical Lead, Implementation Engineer

## Context

Loki uses label-based indexing. High-cardinality labels (user_id, request_id, session_id) cause:
- Index explosion → OOM, slow queries, high storage cost
- Cardinality alerts needed to catch regressions

We need a strategy that enables trace→logs correlation without cardinality explosion.

## Decision

**Low-cardinality labels only + traceID as structured field.**

### Label Set (Indexed)
| Label | Source OTel Attribute | Values | Cardinality |
|-------|----------------------|--------|-------------|
| `service_name` | `service.name` | gateway, orders, payments | 3 |
| `deployment_environment` | `deployment.environment` | local, staging, prod | 3 |

**Note on naming:** `otelcol.exporter.loki` sanitizes promoted resource attributes to Prometheus label format — dots become underscores. So `service.name` → `service_name`, `deployment.environment` → `deployment_environment`. This is automatic; no relabeling step needed.

**Max series:** 3 × 3 = 9 (negligible)

### Structured Log Fields (Not Indexed)
- `traceID` — Full 32-char hex (extracted via JSON pipeline)
- `spanID` — For span-level correlation
- `message` — Human-readable
- `attrs.*` — Arbitrary key-values

### Correlation Mechanism
1. OTel SDK injects `trace_id` into log record via `LoggingHandler`
2. `otelcol.processor.attributes` inserts `loki.resource.labels` hints to promote `service.name` and `deployment.environment` to Loki labels
3. Grafana data link: `{traceID="<trace_id>"}` → Loki query
4. **Not** a permanent label — `traceID` stays as a structured field, extracted at query time

## Consequences

### Positive
- **Zero cardinality risk** from traceIDs
- **Correlation works:** Click trace → Loki filtered by traceID
- **Cost control:** Labels stay bounded regardless of traffic volume

### Negative
- Label names differ from OTel attribute names (cosmetic, but documented)
- Correlation requires Loki pipeline config (extra complexity)

### Neutral
- OTel semantic conventions for log attributes followed

## Alternatives Considered

1. **traceID as permanent label** — Rejected: cardinality = request count; kills Loki
2. **No traceID in logs** — Rejected: breaks trace→logs correlation (job requirement)
3. **Separate trace index** — Rejected: over-engineering; Loki can do this natively

## References

- [Loki Label Best Practices](https://grafana.com/docs/loki/latest/best-practices/)
- [OTel Log Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/logs/)
- [otelcol.exporter.loki documentation](https://grafana.com/docs/alloy/latest/reference/components/otelcol.exporter.loki/)
- AI Execution Roadmap, ADR-009