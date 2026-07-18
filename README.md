# Observatory

**A production-grade observability platform demonstrating LGTM stack expertise, OpenTelemetry instrumentation, SLO-based alerting, and observability-as-a-practice.**

> **Live Demo:** [observatory-demo.example.com](https://observatory-demo.example.com) (read-only Grafana Cloud)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Demo Applications                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                      │
│  │   Gateway   │───▶│   Orders    │    │  Payments   │  (Python FastAPI)    │
│  │  (FastAPI)  │    │  (FastAPI)  │    │  (FastAPI)  │  + OTel SDK         │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘                      │
└─────────┼──────────────────┼──────────────────┼──────────────────────────────┘
          │                  │                  │
          ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      Grafana Alloy (OTel Collector)                         │
│         Metrics → Mimir    Logs → Loki    Traces → Tempo                    │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Grafana (Provisioned)                                │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌────────────────────┐ │
│  │ Infra/RED    │ │ Reliability  │ │ Business KPI │ │ Trace/Log          │ │
│  │ Dashboard    │ │ /SLO/Budget  │ │ Dashboard    │ │ Correlation        │ │
│  └──────────────┘ └──────────────┘ └──────────────┘ └────────────────────┘ │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │              Before/After Dashboard Redesign Case Study                │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## What This Demonstrates

| Competency | Evidence |
|------------|----------|
| **Grafana / LGTM Stack** | Full stack running, correlated via Alloy |
| **OpenTelemetry** | Auto + manual instrumentation, exemplars, traceID injection |
| **SLOs & Burn-Rate Alerting** | Multi-window multi-burn-rate, error budget dashboard, simulator |
| **Terraform + Ansible** | TF: Grafana provider (dashboards, alerts, SLOs); Ansible: fleet bootstrap |
| **Dashboard as Code** | JSON in repo, Terraform-managed, CI-validated, before/after case study |
| **Consumer Onboarding** | 15-min runbook, stakeholder briefs, 5 training lessons |

---

## Quickstart

```bash
# Prerequisites: Docker, Docker Compose, make
git clone https://github.com/MarkusIsaksson1982/observatory
cd observatory
make up

# Wait ~60s, then open:
#   Grafana:    http://localhost:3000 (admin/admin)
#   Gateway:    http://localhost:8000
#   Alloy:      http://localhost:12345
#   Mimir:      http://localhost:9009
#   Tempo:      http://localhost:3200
#   Loki:       http://localhost:3100

make validate  # Health check all services
make down      # Clean shutdown
```

---

## Screenshot

![Service Health RED Dashboard](docs/screenshots/service-health-red.png)

*Service Health dashboard showing RED metrics per service with exemplars linking to traces.*

---

## Key Documentation

| Document | Purpose |
|----------|---------|
| [SHOWCASE.md](SHOWCASE.md) | 5-minute hiring overview |
| [PROJECT_CONSTITUTION.md](PROJECT_CONSTITUTION.md) | Frozen governance |
| [ROADMAP.md](ROADMAP.md) | Timeline & decisions |
| [ADR/](ADR/) | Architecture decisions |
| [docs/PORTFOLIO_EVIDENCE.md](docs/PORTFOLIO_EVIDENCE.md) | Job req → artifact mapping |

---

## Repository Structure

```
observatory/
├── PROJECT_CONSTITUTION.md     # Frozen governance
├── ROADMAP.md                  # Timeline & decisions
├── DESIGN_PRINCIPLES.md        # 12 principles
├── CAPABILITY_MATRIX.md        # Living capability tracking
├── IMPLEMENTATION_STATUS.md    # Daily progress
├── DECISION_LOG.md             # Captain's log
├── ADR/                        # Frozen ADRs
├── apps/gateway/               # FastAPI + OTel instrumentation
├── alloy/config.river          # Alloy pipeline config
├── grafana/provisioning/       # Datasources + dashboards
├── mimir/, loki/, tempo/       # LGTM configs
├── terraform/                  # Grafana provider (Phase 5)
├── ansible/                    # Fleet bootstrap (Phase 5)
├── scripts/                    # Load gen, fault injection
└── .github/workflows/          # CI: lint, validate
```

---

## License

MIT License — see [LICENSE](LICENSE)