# ADR-011: Tempo metrics-generator as primary RED metrics source

**Status:** Accepted
**Date:** 2026-07-21
**Deciders:** Technical Lead, Implementation Engineer, Claude Sonnet 5 (senior planner review)

## Context

Observatory needs a single authoritative source for RED metrics:

- **Request rate**
- **Error rate**
- **Duration / latency**

These metrics are used by:

- the `Service Health - RED Dashboard`,
- the Sloth-generated SLO recording and alerting rules,
- the System Overview dashboard,
- future error-budget and burn-rate views.

After Mimir and Tempo were both live, the project had two independent trace-derived metric paths writing into Mimir:

1. **Alloy spanmetrics connector**

   ```text
   OTLP traces → Alloy spanmetrics connector → Mimir
   ```

   Metric family example:

   ```text
   traces_span_metrics_calls_total
   traces_span_metrics_duration_milliseconds_bucket
   ```

2. **Tempo metrics-generator**

   ```text
   OTLP traces → Tempo → Tempo metrics-generator → Mimir
   ```

   Metric family example:

   ```text
   traces_spanmetrics_calls_total
   traces_spanmetrics_latency_bucket
   traces_spanmetrics_size_total
   ```

Both sources were confirmed live in Mimir.

The original implementation plan treated Alloy's spanmetrics connector as the primary RED metrics source. That choice made sense earlier in the project because Alloy was already the central OTLP collector and Tempo's metrics-generator was not yet wired to Mimir.

However, once Tempo's metrics-generator was enabled and verified, keeping both sources active created several problems:

- **Double-counting risk:** if dashboards or SLOs accidentally summed both metric families, request/error/latency metrics would be inflated.
- **Label divergence:** Alloy and Tempo emit different label names.
- **Operational ambiguity:** two sources of truth for the same RED signals.
- **Portfolio clarity:** the repository should demonstrate one deliberate metrics architecture, not two overlapping pipelines.

The two sources also differ in capability:

| Capability | Alloy spanmetrics | Tempo metrics-generator |
|---|---:|---:|
| Derives RED metrics from traces | Yes | Yes |
| Writes directly to Mimir | Yes | Yes |
| Supports exemplars for metric-to-trace click-through | Limited / indirect | Native, with `send_exemplars: true` |
| Aligns with Grafana Labs trace-to-metrics architecture | Partially | Strongly |
| Uses Tempo as the trace-aware metrics generation point | No | Yes |
| Generator-side storage/WAL buffering for remote write | Not applicable | Yes |

A further practical finding was that Tempo's span-metrics histogram buckets do **not** use the usual Prometheus-style round-number boundaries. This had a direct impact on SLO queries, especially the latency SLO targeting requests completing within 500 ms.

## Decision

**Tempo metrics-generator is the primary source of RED metrics for Observatory.**

Alloy's spanmetrics connector is retained in the configuration for reference and fallback, but its metrics output is disabled:

```river
otelcol.connector.spanmetrics "default" {
  // ...
  output {
    metrics = []  // Disabled: Tempo metrics-generator is primary (ADR-011)
  }
}
```

The RED dashboard and SLO rules use Tempo-generated metric families:

```text
traces_spanmetrics_calls_total
traces_spanmetrics_latency
traces_spanmetrics_latency_bucket
traces_spanmetrics_latency_count
traces_spanmetrics_size_total
```

The primary RED queries filter on server spans:

```promql
span_kind="SPAN_KIND_SERVER"
```

Error-rate queries use Tempo's OTel span-status label:

```promql
status_code="STATUS_CODE_ERROR"
```

Example request-rate query:

```promql
sum(
  rate(
    traces_spanmetrics_calls_total{
      span_kind="SPAN_KIND_SERVER"
    }[5m]
  )
) by (service)
```

Example error-rate query:

```promql
sum(
  rate(
    traces_spanmetrics_calls_total{
      span_kind="SPAN_KIND_SERVER",
      status_code="STATUS_CODE_ERROR"
    }[5m]
  )
) by (service)
/
sum(
  rate(
    traces_spanmetrics_calls_total{
      span_kind="SPAN_KIND_SERVER"
    }[5m]
  )
) by (service)
* 100
```

Example latency quantile query:

```promql
histogram_quantile(
  0.95,
  sum(
    rate(
      traces_spanmetrics_latency_bucket{
        span_kind="SPAN_KIND_SERVER"
      }[5m]
    )
  ) by (service, le)
)
```

Tempo's metrics-generator is configured with additional span-metrics dimensions:

```yaml
metrics_generator:
  processor:
    span_metrics:
      dimensions:
        - http.method
        - http.route
        - http.status_code
```

Tempo remote-writes generated metrics to Mimir with exemplars enabled:

```yaml
metrics_generator:
  storage:
    remote_write:
      - url: http://mimir:9009/api/v1/push
        send_exemplars: true
```

This decision does **not** replace Alloy as the central collector. Alloy remains responsible for:

- receiving OTLP logs and traces,
- exporting logs to Loki,
- exporting traces to Tempo,
- scraping infrastructure metrics from Alloy and Loki,
- remote-writing scraped infrastructure metrics to Mimir.

The decision is scoped specifically to **trace-derived RED metrics**.

## Consequences

### Positive

- **Single source of truth for RED metrics.**
  Dashboards and SLOs query one metric family, eliminating accidental double-counting from two trace-derived metric sources.

- **Stronger metric-to-trace correlation.**
  Tempo metrics-generator emits exemplars, and `send_exemplars: true` allows Mimir to retain exemplar trace IDs. This supports click-through from a metric spike in Grafana directly into the relevant Tempo trace.

- **Better alignment with Grafana Labs architecture.**
  Using Tempo's metrics-generator demonstrates the Grafana-recommended pattern where Tempo derives service-level metrics from traces and forwards them to Mimir.

- **More advanced portfolio signal.**
  Tempo metrics-generator is a more specialized trace-derived metrics mechanism than a generic collector-side spanmetrics connector. It shows understanding of:
  - trace-to-metrics pipelines,
  - exemplars,
  - Mimir remote write,
  - SLOs built from trace-derived metrics,
  - Tempo generator configuration.

- **Cleaner operational story.**
  RED metrics are generated close to the trace storage backend. If a trace exists in Tempo, the corresponding RED metrics can be reasoned about as coming from the same trace pipeline.

- **Generator-side buffering.**
  Tempo's metrics-generator uses local storage/WAL-style buffering under `/var/tempo/generator`, making the metrics-generation path more robust than a purely stateless transform.

- **Avoids duplicate ingestion cost.**
  Only one trace-derived RED metric family is written to Mimir, reducing unnecessary series churn and query ambiguity.

### Negative

- **Label names differ from the log pipeline.**
  Loki logs use labels such as `service_name`. Tempo metrics use `service`. This means dashboards and queries must remember that metrics and logs do not share identical label names.

- **Error semantics are OTel span status, not HTTP status.**
  The primary error label is `status_code="STATUS_CODE_ERROR"`. This represents OpenTelemetry span status, not necessarily HTTP `5xx` or `429` responses. The custom `http.status_code` dimension can be used where HTTP-status-based analysis is required, but the primary availability SLO currently uses OTel span status.

- **Tempo histogram buckets required configuration.**
  Tempo's default histogram boundaries are powers of two, not round numbers. Custom `histogram_buckets` must be configured to get exact thresholds (e.g., `le="0.5"` for 500ms). This is a one-time config change, now applied.

- **Latency values are expressed in seconds.**
  Tempo's `traces_spanmetrics_latency` histogram uses seconds. Dashboards that display milliseconds must use Grafana unit handling correctly or multiply by 1000 where appropriate.

- **Tempo becomes critical for RED metrics and SLOs.**
  If Tempo's metrics-generator is disabled, misconfigured, or unable to remote-write to Mimir, RED dashboards and SLO recording rules lose their primary data source.

- **Alloy spanmetrics remains present but disabled.**
  The connector is intentionally retained as a fallback, but this creates a small risk of confusion. The disabled output must be clearly documented.

### Neutral

- **Alloy remains the collector for logs and traces.**
  This decision does not change ADR-001. Alloy is still the OTLP entry point and collector.

- **Recording-rule abstraction deferred.**
  A canonical recording-rule layer could later normalize Tempo labels into a common metric model (e.g., `service` → `service_name`). This is not required now because Tempo is the only active RED source.

- **Fallback path retained.**
  Alloy spanmetrics can be re-enabled by changing `output { metrics = [] }` to forward into the Prometheus exporter path. However, re-enabling it would require either disabling Tempo metrics-generator or introducing explicit normalization/recording rules to avoid double-counting.

## Technical detail: Tempo histogram buckets and `le="0.5"`

Tempo's default span-metrics histogram buckets use powers of two divided by 1000 (`le = 2^n / 1000`), not the usual Prometheus round-number boundaries. This means `le="0.5"` does not exist by default — the closest bucket is `le="0.512"` (= 2^9/1000).

### Resolution

Custom histogram boundaries are configured in `tempo.yml`:

```yaml
metrics_generator:
  processor:
    span_metrics:
      dimensions:
        - http.method
        - http.route
        - http.status_code
      histogram_buckets:
        - 0.05
        - 0.1
        - 0.25
        - 0.5
        - 1
        - 2.5
        - 5
        - 10
```

This replaces Tempo's default power-of-two buckets with standard Prometheus-style boundaries, including an exact `le="0.5"` bucket. The SLO latency threshold of 500ms is now measured precisely.

### Why `le="0.5"` initially appeared plausible but returned empty

Mimir's global label-values endpoint (`/api/v1/label/le/values`) shows `0.5` as an `le` label value — but this comes from other metrics (Alloy, Mimir internals), not from Tempo's `traces_spanmetrics_latency_bucket`. The correct verification is metric-specific:

```promql
traces_spanmetrics_latency_bucket{
  service="gateway",
  span_kind="SPAN_KIND_SERVER",
  le="0.5"
}
```

Before custom buckets were configured, this returned empty while `le="0.512"` returned data. After configuring custom buckets, `le="0.5"` returns data as expected.

### Effect on Sloth SLO rules

The latency SLO uses `le="0.5"` to measure requests completing within 500ms:

```promql
sum(
  rate(
    traces_spanmetrics_latency_bucket{
      service="gateway",
      span_kind="SPAN_KIND_SERVER",
      le="0.5"
    }[5m]
  )
)
/
sum(
  rate(
    traces_spanmetrics_latency_count{
      service="gateway",
      span_kind="SPAN_KIND_SERVER"
    }[5m]
  )
)
```

When using fixed-bucket latency SLOs, the selected `le` value must always match an actual histogram bucket emitted by the metric source.

## Related decisions

- **ADR-001:** Collector Choice — Grafana Alloy. Alloy remains the OTLP collector for logs and traces.
- **ADR-010:** SLO Implementation via Sloth, and Terraform Migration Timing. Sloth remains the SLO rule generator; this ADR changes the underlying metric source used by the SLO queries.
