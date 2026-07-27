# Showcase — Observatory

**For hiring managers with 5 minutes.**

---

## What Is This?

A **production-grade observability platform** demonstrating end-to-end LGTM stack expertise, OpenTelemetry instrumentation, SLO-based alerting with burn-rate detection, and observability-as-a-practice — all runnable locally with `docker compose up`.

---

## Why Should You Care?

| If You're Hiring For... | This Proves... |
|------------------------|----------------|
| **Observability Engineer** | Full LGTM + Alloy + OTel + correlation + burn-rate SLOs |
| **Platform Engineer** | Terraform (Grafana provider) + Ansible fleet bootstrap + dashboard-as-code |
| **SRE** | Error budgets, multi-window burn-rate alerts, runbooks, postmortems |
| **Backend Engineer** | FastAPI + OTel auto/manual instrumentation, exemplars, structured logging |
| **DevOps Engineer** | Docker Compose, CI gates, `make up`/`validate`, zero-click local demo |

---

## Three Most Impressive Things

### 1. Telemetry-First Architecture
Not "Grafana dashboards on top of Prometheus." The pipeline starts at **code instrumentation** (OTel SDK + auto-instrumentation) → **Alloy** (vendor-neutral collector) → **Mimir/Loki/Tempo** (purpose-built storage) → **Grafana** (three dashboard genres for three audiences). Every signal flows with exemplars and `traceID` labels enabling click-through correlation.

### 2. SLOs That Actually Page People
No static thresholds. **Multi-window, multi-burn-rate alerts** (Google SRE Workbook) catch both fast burns (severe, short) and slow burns (subtle, long). A synthetic fault injector triggers real alerts → error budget dashboard drains → runbook links → postmortem with action items. This is observability **practice**, not tooling.

### 3. Dashboard Design as Communication
Three genres, three audiences:
- **Infra/RED** → On-call engineer: "Is the service healthy right now?"
- **Reliability/SLO** → SLO owner: "Are we burning error budget?"
- **System Overview** → Platform engineer: "Is the full stack healthy?"
Plus a **before/after redesign case study** with written rationale per change — proving "dashboard design principles" (job req) not just "I made dashboards."

---

## Engineering Skills Demonstrated

| Category | Evidence |
|----------|----------|
| **LGTM Stack** | `docker-compose.yml`, `alloy/config.river`, `grafana/provisioning/` |
| **OpenTelemetry** | `apps/gateway/instrumentation.py` — auto + manual spans, exemplars, traceID logs |
| **SLOs & Burn-Rate** | `sloth/gateway-slo.yaml`, `sloth/gateway-slo-rules.yaml`, `mimir-rules/tenant-0/` |
| **Terraform** | `terraform/dashboards.tf`, `terraform/datasources.tf`, `terraform/alerts.tf` — Grafana provider as code |
| **Ansible** | `ansible/playbook.yml`, `ansible/group_vars/all.yml` — host provisioning with Jinja2 templating |
| **Dashboard as Code** | Terraform `grafana_dashboard` resources, CI validation |
| **Consumer Onboarding** | `docs/onboarding-guide.md` — 15-min timed runbook |
| **Incident Practice** | `references/PLAYBOOK.md` — 5 scripted demo scenarios with interview Q&A |
| **Documentation** | ADRs, runbooks, stakeholder briefs, architecture fitness checklist |

---

## How to Run It (2 Minutes)

```bash
git clone https://github.com/MarkusIsaksson1982/observatory
cd observatory
make up

# Wait ~60s
# Open http://localhost:3000 (Grafana) — admin / admin
# Dashboard "Service Health" shows live RED metrics
# Click a trace → "Logs for this trace" → Loki opens filtered by traceID
```

**Requirements:** Docker, Docker Compose, `make`. No cloud accounts, no Kubernetes.

---

## Where to Look in the Repository

| Interest | Start Here |
|----------|------------|
| Architecture | `DECISION_LOG.md` (governance), `ADR/` (decisions) |
| Telemetry Pipeline | `alloy/config.river`, `apps/gateway/instrumentation.py` |
| Dashboards | `grafana/provisioning/dashboards/` (JSON) |
| SLOs & Alerting | `sloth/gateway-slo.yaml`, `mimir-rules/tenant-0/` |
| Terraform / Ansible | `terraform/`, `ansible/` |
| Onboarding | `docs/onboarding-guide.md`, `docs/deployer-guide.md` |
| Portfolio Mapping | `docs/PORTFOLIO_EVIDENCE.md` |

---

## Live Demo

**Public Read-Only Grafana Cloud:** [observatory-demo.example.com](https://observatory-demo.example.com)

No setup required. Same dashboards, same data, read-only.

---

## Contact

**Markus Isaksson** — Observability & Platform Engineering  
📧 markus@isaksson.dev | 🔗 [LinkedIn](https://linkedin.com/in/markusisaksson) | 🐙 [GitHub](https://github.com/MarkusIsaksson1982)

---

*Built as a portfolio demonstration of observability engineering practice.*