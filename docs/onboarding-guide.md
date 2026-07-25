# Onboarding Guide — Add a new service in 15 minutes

**Goal:** Guide a consumer team from zero OTel to business value — trace → logs → dashboard → SLO.
**Persona:** Backend team owning `orders` service (or any new service)
**Timebox:** 15 min

### Prerequisites
- Observatory up: `make up && cd terraform && terraform apply -auto-approve`
- Service language: Python (FastAPI example), but pattern applies to Go/Node

### Minute 0-3 — Instrument

```python
# instrumentation.py — copy from apps/gateway/instrumentation.py
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
# Resource must set deployment.environment as literal string, not semconv constant
# Matches ADR-003 and alloy/config.river loki_hints
resource = Resource.create({
  "service.name": "orders",
  "deployment.environment": os.getenv("ENVIRONMENT", "local")
})
# FastAPIInstrumentor().instrument_app(app) AFTER app creation
```

Add 3 manual spans: `http.client` for outbound calls, `business.operation` for domain logic.

### Minute 3-6 — Ship via Alloy

No sidecar needed locally — gateway already sends OTLP to Alloy at `alloy:4317`. Verify:
- `alloy/config.river` already has `otelcol.receiver.otlp` → `otelcol.exporter.otlphttp.loki` + `otelcol.exporter.otlp.tempo`
- Logs: low-cardinality labels only (`service_name`, `deployment_environment`) — traceID stays as structured metadata (ADR-003)

### Minute 6-9 — Register in Terraform

Add a dashboard resource to `terraform/dashboards.tf`:

```hcl
resource "grafana_dashboard" "orders" {
  config_json = file("${path.module}/../grafana/provisioning/dashboards/service-health-red.json")
  folder      = grafana_folder.service_health.id
  overwrite   = true
}
```

Add to `terraform/variables.tf` if needed. `terraform plan` should show 1 to add (dashboard), 0 to change — no drift.

### Minute 9-12 — Define SLO

Copy `sloth/gateway-slo.yaml` → `sloth/orders-slo.yaml`, change `service: orders`, keep `le="0.5"` (custom buckets already in `tempo/tempo.yml` per ADR-011). Generate:

```bash
docker run --rm -v $PWD/sloth:/input slok/sloth:latest generate -i /input/orders-slo.yaml -o /input/orders-slo-rules.yaml --no-color
```

Copy to `mimir-rules/tenant-0/`. Mimir reloads rules from local filesystem.

### Minute 12-15 — Verify business value

1. `python tools/load-generator.py --rate 10 --duration 60` — generates `traces_spanmetrics_*`
2. Grafana → Service Health RED: filter `service="orders"` — request rate appears
3. Click trace → Logs — Loki query `{service_name="orders"} | json | traceID="<id>"` — OTLP/HTTP structured metadata path, not regex
4. `python tools/fault-injector.py --probe-only` — proves `/orders` returns 503 (natural failure, no gateway change needed) → burn-rate panel becomes non-empty

**Done criteria:**
- Trace appears in Tempo, logs correlate, dashboard populates, SLO burn-rate has data
- Consumer can now answer "Is orders healthy?" and "Are we burning budget?" without paging platform team

**Anti-patterns to avoid:**
- Don't add `user_id` label — cardinality explosion
- Don't use `${DS_PROMETHEUS}` in provisioned JSON — use UID `mimir`
- Don't query `service_name` in Sloth metrics — use `sloth_service`
- Don't reference Terraform modules that don't exist — use direct `grafana_dashboard` resources
