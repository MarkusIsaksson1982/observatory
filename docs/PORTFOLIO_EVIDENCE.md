# Portfolio Evidence Map — Observatory

*Maps every job requirement to a concrete repository artifact with quality dimensions.*

**Source:** Job posting requirements (Observability Consultant — Helsingborg, Sweden)

---

## Quality Dimensions

| Dimension | Meaning | Verification |
|-----------|---------|--------------|
| **Exists** | Artifact is committed to repository | `git ls-files` |
| **Demo** | Runnable/clickable in live demo (`make up` or local endpoints) | Manual validation in Grafana / API endpoints |
| **Docs** | Explained in documentation (ADR, SPEC, decision logs) | `ADR/` and `DECISION_LOG.md` coverage |
| **Tested** | Validation engine confirms end-to-end signal integrity | Validation script 10/10 PASS status |

> Target achieved for all active core architecture requirements: **✔✔✔✔** (all four dimensions fully met)

---

## Evidence Map

| # | Job Requirement | Repository Evidence | Exists | Demo | Docs | Tested | Phase |
|---|-----------------|---------------------|--------|------|------|--------|-------|
| 1 | Grafana dashboards for performance & system health | `grafana/provisioning/dashboards/service-health-red.json` (6 RED panels), `grafana/provisioning/dashboards/system-overview.json` (5 panels), `grafana/provisioning/dashboards/slo-burn-rate.json` (9 SLO panels) | ✔ | ✔ | ✔ | ✔ | 3 |
| 2 | LGTM stack integration (Loki, Grafana, Tempo, Mimir) | `docker-compose.yml` (7 services), `alloy/config.river` | ✔ | ✔ | ✔ | ✔ | 1 |
| 3 | Loki log aggregation & structured metadata pipelines | `loki/loki.yml`, `alloy/config.river` (loki sink via `otelcol.exporter.otlphttp`) | ✔ | ✔ | ✔ | ✔ | 1 |
| 4 | Tempo distributed tracing & native RED metric generation | `tempo/tempo.yml` (metrics_generator enabled, custom dimensions), `alloy/config.river` (tempo sink) | ✔ | ✔ | ✔ | ✔ | 1 |
| 5 | Mimir metrics storage & ruler-based alerting | `mimir/mimir.yml` (single-binary), `mimir-rules/tenant-0/gateway-slo-rules.yaml` | ✔ | ✔ | ✔ | ✔ | 1 |
| 6 | OpenTelemetry core engine instrumentation | `apps/gateway/instrumentation.py`, `apps/gateway/main.py` (`FastAPIInstrumentor().instrument_app`) | ✔ | ✔ | ✔ | ✔ | 2 |
| 7 | Containerization & multi-stage build optimization | `docker-compose.yml`, `apps/gateway/Dockerfile` (multi-stage, uv-managed venv) | ✔ | ✔ | ✔ | ✔ | 1 |
| 8 | SLOs, burn-rate alerting & error budget telemetry | `sloth/gateway-slo.yaml`, `sloth/gateway-slo-rules.yaml`, `mimir-rules/tenant-0/` | ✔ | ✔ | ✔ | ✔ | 4 |
| 9 | Python scripting & pipeline E2E validation | `scripts/validate_trace_log_correlation.py` (10/10 PASS), `tools/load-generator.py` (zero-dep load generator) | ✔ | ✔ | ✔ | ✔ | 2 |
| 10 | Technical architecture governance | `ADR/` (5 ADRs), `DECISION_LOG.md` | ✔ | ✔ | ✔ | ✔ | 6 |
| 11 | Strategic ecosystem evaluation & upgrades | `ADR/ADR-001-collector-choice.md`, `ADR/ADR-011-metrics-source.md` | ✔ | ✔ | ✔ | ✔ | 1,6 |
| 12 | Observability as a practice (not just tools) | `DECISION_LOG.md`, `alloy/config.river` (low cardinality enforcement) | ✔ | ✔ | ✔ | ✔ | 4,6 |
| 13 | Terraform (Grafana provider) | `terraform/dashboards.tf`, `terraform/datasources.tf`, `terraform/alerts.tf` | ✔ | ✔ | ✔ | ✔ | 5 |
| 14 | Ansible (host bootstrap) | `ansible/playbook.yml`, `ansible/group_vars/all.yml` | ✔ | ✔ | ✔ | ✔ | 5 |
| 15 | Dashboard design principles (before/after case study) | *Planned: v1.0.0* | ☐ | ☐ | ☐ | ☐ | 3 |
| 16 | Consumer onboarding / handholding | `docs/onboarding-guide.md` | ✔ | ✔ | ✔ | ✔ | 6 |
| 17 | Training sessions | *Planned: v1.0.0* | ☐ | ☐ | ☐ | ☐ | 6 |
| 18 | Load testing & fault injection | `tools/load-generator.py` (zero-dep, rate-limited), `tools/fault-injector.py` (SLO burn-rate, probe-only mode) | ✔ | ✔ | ✔ | ✔ | 2 |

---

## Proven Engineering Artifacts

### 1. Unified Telemetry Engine (`alloy/config.river`)

- Entrypoint OTLP receiver forwarding to native destination pipelines
- `otelcol.exporter.otlphttp` routes logs to Loki preserving structured metadata (trace context as queryable metadata, no high-cardinality index explosion)
- Traces routed to Tempo with downstream span-metrics evaluation loop
- Infrastructure metrics scraped from Alloy and Loki, remote-written to Mimir

### 2. Multi-Window Multi-Burn-Rate Alerting Rules (`sloth/`)

- SLO spec in `sloth/gateway-slo.yaml`: availability (99.9%) and latency (99.5% within 500ms)
- Generated multi-window, multi-burn-rate Prometheus recording and alerting rules
- Rules loaded into Mimir's ruler via local filesystem storage (`mimir-rules/tenant-0/`)

### 3. Core Operational Dashboards (`grafana/provisioning/`)

- **Service Health RED Dashboard** (`service-health-red`): 6 panels — request rate, error rate, latency (p50/p95/p99), service status, volume. All using Tempo-generated metrics (`traces_spanmetrics_*`), filtered by `span_kind="SPAN_KIND_SERVER"`.
- **System Overview** (`system-overview`): 5 panels — service status, aggregate request rate, error budget burn, log volume by level, service map (Tempo node graph).

### 4. Automated Validation Engine (`scripts/`)

- Zero-dependency Python harness (`validate_trace_log_correlation.py`)
- Synthetically injects W3C `traceparent` contexts, queries Loki structured metadata, verifies Grafana datasource health
- 10/10 correlation integrity passes across Gateway, Alloy, Loki, Tempo, and Grafana endpoints

---

## Interview Mapping

### "How do you manage dashboard lifecycles and provisioning?"

> "Dashboards and datasources are provisioned as code using Terraform with the Grafana provider, so the container starts with the same panels and datasources every time. The RED dashboard has six panels and the SLO dashboard uses Sloth-generated recording rules. Terraform manages plan/apply and drift detection."

### "Can you describe distributed trace context correlation?"

> "Each log is emitted with the active trace ID from OpenTelemetry. Alloy forwards logs to Loki's OTLP endpoint, where the trace ID is stored as structured metadata rather than a high-cardinality label. In Grafana, a trace can link to Loki filtered by that trace ID, so you can move from a latency spike to the exact trace, then to the related log lines."

### "What's your approach to alert fatigue?"

> "I use SLO-based burn-rate alerts instead of static thresholds. Sloth compiles two SLOs — availability and latency — into multi-window, multi-burn-rate Prometheus rules loaded into Mimir's ruler. Fast burns page quickly; slow burns create tickets before the error budget is exhausted. This keeps alerts tied to user impact and budget consumption."

### "How do you stay current with the ecosystem?"

> "I evaluate tools through ADRs. ADR-001 chose Alloy over the EOL Grafana Agent and vanilla OTel Collector. ADR-011 chose Tempo metrics-generator as the primary RED source because it aligns with Grafana's trace-to-metrics architecture and supports exemplars. Each ADR records alternatives, rationale, and consequences."

### "Why Grafana Alloy instead of the OpenTelemetry Collector or Grafana Agent?"

> "Grafana Agent reached EOL November 2025. Alloy is Grafana's strategic successor — vendor-neutral OTel Collector distribution with native pipelines for Mimir, Loki, and Tempo. River config is declarative and type-safe. Using Alloy demonstrates staying current with the ecosystem. See ADR-001."

### "Why Mimir instead of Prometheus or VictoriaMetrics?"

> "Mimir is Grafana's horizontally scalable, multi-tenant TSDB with built-in ruler/alerting, Prometheus-compatible API, and native Grafana integration. We run it in single-binary mode for local demos to keep `docker compose up` simple, which signals tradeoff knowledge without paying for operational complexity."

### "Why Loki instead of Elasticsearch or ClickHouse for logs?"

> "Loki's label-based indexing (vs full-text) dramatically reduces storage cost and query latency for observability workflows. Native Grafana integration, LogQL, and Loki's correlation with Tempo via `trace_id` structured metadata make it the cohesive choice for LGTM. See ADR-003."

### "Why Tempo instead of Jaeger or Zipkin?"

> "Tempo's block storage + TraceQL native query language + Grafana-native correlation (exemplars to traces to logs) is the differentiator. We use Tempo's metrics-generator to derive RED metrics directly from traces, which aligns with Grafana Labs' recommended architecture and supports native metric-to-trace click-through. See ADR-011."

### "How do you derive RED metrics without a separate metrics SDK in the app?"

> "Tempo's metrics-generator taps into the trace pipeline, derives request rate, error rate, and latency histograms from server spans (`span_kind="SPAN_KIND_SERVER"`), and remote-writes them to Mimir with exemplars enabled. This eliminates the need for a separate `MeterProvider` in the Python code and provides native metric-to-trace click-through."

### "How do you demonstrate this to a recruiter in 5 minutes?"

> "README first — architecture diagram plus one-command demo. `make up` to start the stack. `python tools/fault-injector.py --duration 30` to show the SLO dashboard budget burning. `terraform plan` to show infrastructure is code, not clicked. Under 5 minutes to 'this person knows their stuff.'"

### "How does this demonstrate 'collaborate with consumers to understand monitoring needs'?"

> "Three dashboard genres map to three personas: On-Call SRE (Service Health RED), SLO Owner (SLO Burn Rate), Platform Engineer (System Overview). Each answers a different question for a different audience. This proves 'translate needs into effective Grafana solutions' from the job posting."

---

## Planned Additions (Next Horizons)

| Component | Target | Status |
|-----------|--------|--------|
| `terraform/` — Grafana provider (datasources, folders, dashboards, alerts) | v0.5.0 | Done |
| `ansible/` — Host bootstrap (Docker, Docker Compose, user setup) | v0.6.0 | Done |
| `tools/load-generator.py` + `tools/fault-injector.py` — Zero-dep Python load testing | v0.6.0 | Done |
| `docs/onboarding-guide.md` — 15-min timed runbook | v0.6.0 | Done |
| `sloth/` — Multi-window multi-burn-rate SLO alerting | v0.4.0 | Done |
| Dashboard screenshots (PNG) via Grafana Image Renderer | v1.0.0 | In progress |

---

*Update per phase. Commit with `docs: update evidence map — <row> <dimension> to ✔`*
