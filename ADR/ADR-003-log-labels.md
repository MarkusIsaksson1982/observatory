# ADR-003: Log Label Strategy — Low Cardinality, traceID as Label

**Status:** Accepted
**Date:** 2025-07-18
**Deciders:** Technical Lead, Implementation Engineer

## Context

Loki uses label-based indexing. High-cardinality labels (user_id, request_id, session_id) cause:
- Index explosion → OOM, slow queries, high storage cost
- Cardinality alerts needed to catch regressions

We need a strategy that enables trace→logs correlation without cardinality explosion.

## Decision

**Low-cardinality labels only + traceID as structured field.**

### Label Set (Indexed)
| Label | Values | Cardinality |
|-------|--------|-------------|
| `service` | gateway, orders, payments | 3 |
| `environment` | local, staging, prod | 3 |
| `level` | debug, info, warn, error | 4 |
| `namespace` | app, infra | 2 |

**Max series:** 3 × 3 × 4 × 2 = 72 (negligible)

### Structured Log Fields (Not Indexed)
- `traceID` — Full 32-char hex (extracted via JSON pipeline)
- `spanID` — For span-level correlation
- `message` — Human-readable
- `attrs.*` — Arbitrary key-values

### Correlation Mechanism
1. OTel SDK injects `trace_id` into log record via `LoggingHandler`
2. Alloy Loki sink extracts `traceID` as label via `stage.labels` → **only for correlation queries**
3. Grafana data link: `{traceID="<trace_id>"}` → Loki query
4. **Not** a permanent label — extracted at query time via `stage.json` → `stage.labels` pipeline

## Consequences

### Positive
- **Zero cardinality risk** from traceIDs
- **Correlation works:** Click trace → Loki filtered by traceID
- **Cost control:** Labels stay bounded regardless of traffic volume

### Negative
- Correlation requires Loki pipeline config (extra complexity)
- Can't use `traceID` in Loki retention/streaming rules directly

### Neutral
- OTel semantic conventions for log attributes followed

## Alternatives Considered

1. **traceID as permanent label** — Rejected: cardinality = request count; kills Loki
2. **No traceID in logs** — Rejected: breaks trace→logs correlation (job requirement)
3. **Separate trace index** — Rejected: over-engineering; Loki can do this natively

## References

- [Loki Label Best Practices](https://grafana.com/docs/loki/latest/best-practices/)
- [OTel Log Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/logs/)
- PROJECT_CONSTITUTION.md Section 4 (ADR-009)