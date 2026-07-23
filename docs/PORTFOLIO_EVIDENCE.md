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
| 2 | LGTM stack integration (Loki, Grafana, Tempo, Mimir) | `docker-compose.yml` (6 services), `alloy/config.river` | ✔ | ✔ | ✔ | ✔ | 1 |
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
| 13 | Terraform (Grafana provider) | *Planned: v0.6.0* | ☐ | ☐ | ☐ | ☐ | 5 |
| 14 | Ansible (host bootstrap) | *Planned: v0.6.0* | ☐ | ☐ | ☐ | ☐ | 5 |
| 15 | Dashboard design principles (before/after case study) | *Planned: v1.0.0* | ☐ | ☐ | ☐ | ☐ | 3 |
| 16 | Consumer onboarding / handholding | *Planned: v1.0.0* | ☐ | ☐ | ☐ | ☐ | 6 |
| 17 | Training sessions | *Planned: v1.0.0* | ☐ | ☐ | ☐ | ☐ | 6 |
| 18 | k6 load testing & fault injection | *Planned: v0.6.0+* | ☐ | ☐ | ☐ | ☐ | 2 |

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

> "Dashboards and datasources are provisioned as code in Grafana's YAML provisioning, so the container starts with the same panels and datasources every time. The RED dashboard has six panels and the SLO dashboard uses Sloth-generated recording rules. Terraform is planned for v0.6.0 to add plan/apply and drift detection."

### "Can you describe distributed trace context correlation?"

> "Each log is emitted with the active trace ID from OpenTelemetry. Alloy forwards logs to Loki's OTLP endpoint, where the trace ID is stored as structured metadata rather than a high-cardinality label. In Grafana, a trace can link to Loki filtered by that trace ID, so you can move from a latency spike to the exact trace, then to the related log lines."

### "What's your approach to alert fatigue?"

> "I use SLO-based burn-rate alerts instead of static thresholds. Sloth compiles two SLOs — availability and latency — into multi-window, multi-burn-rate Prometheus rules loaded into Mimir's ruler. Fast burns page quickly; slow burns create tickets before the error budget is exhausted. This keeps alerts tied to user impact and budget consumption."

### "How do you stay current with the ecosystem?"

> "I evaluate tools through ADRs. ADR-001 chose Alloy over the EOL Grafana Agent and vanilla OTel Collector. ADR-011 chose Tempo metrics-generator as the primary RED source because it aligns with Grafana's trace-to-metrics architecture and supports exemplars. Each ADR records alternatives, rationale, and consequences."

---

## Planned Additions (Next Horizons)

| Component | Target | Status |
|-----------|--------|--------|
| `terraform/` — Grafana provider (datasources, folders, dashboards, alerts) | v0.6.0 | Planned |
| `ansible/` — Fleet bootstrap (Docker, Alloy, certs) | v0.6.0 | Planned |
| `apps/orders/`, `apps/payments/` — Microservice stubs for distributed trace story | v0.6.0 | Planned |
| `scripts/load-test.k6.js` — k6 load generation + fault injection | v0.6.0+ | Planned |
| `docs/onboarding-guide.md` — 15-min timed runbook | v1.0.0 | Planned |
| `training/` — 5-part observability training curriculum | v1.0.0 | Planned |
| Before/after dashboard redesign case study | v1.0.0 | Planned |

---

*Update per phase. Commit with `docs: update evidence map — <row> <dimension> to ✔`*
