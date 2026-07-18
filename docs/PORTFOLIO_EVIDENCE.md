# Portfolio Evidence Map — Observatory

*Maps every job requirement to a concrete repository artifact with quality dimensions.*

**Source:** PROJECT_CONSTITUTION.md Section 7 (Enhanced)

---

## Quality Dimensions

| Dimension | Meaning | Verification |
|-----------|---------|--------------|
| **Exists** | Artifact is committed to repository | `git ls-files` |
| **Demo** | Runnable/clickable in live demo (`make up` or public endpoint) | Manual test in Grafana |
| **Docs** | Explained in documentation (ADR, SPEC, runbook, onboarding) | `docs/` search |
| **Tested** | CI validates it (lint, schema, healthcheck, integration) | GitHub Actions log |

> Target for core requirements: **✔✔✔✔** (all four dimensions)

---

## Evidence Map

| # | Job Requirement | Repository Evidence | Exists | Demo | Docs | Tested | Phase |
|---|-----------------|---------------------|--------|------|------|--------|-------|
| 1 | Grafana dashboards for performance, reliability, KPIs | `grafana/dashboards/` (7 JSONs: 3 genres + before/after) | ☐ | ☐ | ☐ | ☐ | 3 |
| 2 | LGTM stack (Loki, Grafana, Tempo, Mimir) | `docker-compose.yml`, `alloy/config.river` | ☐ | ☐ | ☐ | ☐ | 1.5 |
| 3 | Loki log aggregation | `loki/loki.yml`, `alloy/config.river` (loki sink) | ☐ | ☐ | ☐ | ☐ | 1.5 |
| 4 | Tempo distributed tracing | `tempo/tempo.yml`, `alloy/config.river` (tempo sink) | ☐ | ☐ | ☐ | ☐ | 1.5 |
| 5 | Mimir metrics storage | `mimir/mimir.yml`, recording rules | ☐ | ☐ | ☐ | ☐ | 1.5 |
| 6 | OpenTelemetry instrumentation | `gateway/instrumentation.py`, `orders/...`, `payments/...` | ☐ | ☐ | ☐ | ☐ | 2 |
| 7 | Terraform (Grafana provider) | `terraform/main.tf`, `terraform/modules/grafana-*` | ☐ | ☐ | ☐ | ☐ | 5 |
| 8 | Ansible (host bootstrap) | `ansible/playbooks/`, `ansible/roles/docker/`, `ansible/roles/alloy/` | ☐ | ☐ | ☐ | ☐ | 5 |
| 9 | Containerization | `docker-compose.yml`, multi-stage `Dockerfile`s | ☐ | ☐ | ☐ | ☐ | 1 |
| 10 | SLOs & error budgets | `docs/SPEC_SLO.md`, `mimir/rules/burn-rate.yml`, burn-rate simulator | ☐ | ☐ | ☐ | ☐ | 4 |
| 11 | Dashboard design principles | `grafana/dashboards/before-redesign.json`, `after-redesign.json`, `before-after/rationale.md` | ☐ | ☐ | ☐ | ☐ | 3 |
| 12 | Consumer onboarding / handholding | `docs/onboarding-guide.md` (timed 15-min runbook) | ☐ | ☐ | ☐ | ☐ | 6 |
| 13 | Technical documentation | `docs/architecture.md`, `docs/adr/`, `docs/runbooks/` | ☐ | ☐ | ☐ | ☐ | 6 |
| 14 | Training sessions | `training/01-metrics.md` … `training/05-otel.md` + slides + recordings | ☐ | ☐ | ☐ | ☐ | 6 |
| 15 | Staying current / evaluating upgrades | `docs/adr/001-alloy-vs-otel-collector.md`, `docs/adr/003-loki-vs-splunk.md` | ☐ | ☐ | ☐ | ☐ | 1,6 |
| 16 | Observability as practice (not just tools) | Stakeholder briefs, SLOs, cardinality guide, postmortems | ☐ | ☐ | ☐ | ☐ | 4,6 |
| 17 | Python scripting & automation | `scripts/load-generator.py`, `scripts/fault-injector.py`, `scripts/validate.py` | ☐ | ☐ | ☐ | ☐ | 2 |
| 18 | k6 load testing | `scripts/load-test.k6.js` | ☐ | ☐ | ☐ | ☐ | 2 |

---

## Usage

**When a job description mentions "X":**
1. Find row where Requirement ≈ X
2. Link the `Repository Evidence` path
3. If quality dimensions aren't all ✔, that's your prep work

**Example: "Experience with Grafana dashboards"**
> "My dashboard work is in `grafana/dashboards/` — three genres (Infra/RED, Reliability/SLO, Business KPI) plus a before/after redesign case study with written rationale. All provisioned via Terraform, validated in CI. [Link to repo]"

**Example: "Terraform experience"**
> "I use Terraform's Grafana provider to manage datasources, folders, dashboards, alert rules, and SLOs as code. See `terraform/modules/grafana-*`. Drift detection via `terraform plan` in CI. [Link to repo]"

**Example: "Observability as a practice"**
> "Beyond tools: stakeholder briefs drive dashboard design, SLOs with burn-rate alerting protect error budgets, runbooks guide incident response, postmortems generate action items that become PRs. See `docs/stakeholder-briefs/`, `docs/SPEC_SLO.md`, `docs/runbooks/`."

---

## Progress Tracking

| Phase | Target: All Core Rows = ✔✔✔✔ |
|-------|-------------------------------|
| Phase 1 | Rows 2, 3, 4, 5, 9 = ✔✔✔✔ |
| Phase 2 | Row 6, 17, 18 = ✔✔✔✔ |
| Phase 3 | Rows 1, 11 = ✔✔✔✔ |
| Phase 4 | Rows 10, 16 = ✔✔✔✔ |
| Phase 5 | Rows 7, 8 = ✔✔✔✔ |
| Phase 6 | Rows 12, 13, 14, 15 = ✔✔✔✔ |
| Phase 7 | All rows = ✔✔✔✔ |

---

## Interview Cheat Sheet

| If They Ask... | You Say... | Point To |
|----------------|------------|----------|
| "Grafana dashboards?" | Three genres for three audiences + before/after case study | `grafana/dashboards/`, `before-after/rationale.md` |
| "LGTM stack?" | All four running, correlated via Alloy | `docker-compose.yml`, `alloy/config.river` |
| "SLOs?" | Burn-rate alerts (fast + slow), error budget dashboard, simulator | `docs/SPEC_SLO.md`, `mimir/rules/` |
| "Terraform?" | Grafana provider managing all Grafana resources | `terraform/modules/grafana-*` |
| "Ansible?" | Fleet bootstrap: Docker, Alloy, certs — NOT Grafana resources | `ansible/roles/alloy/` |
| "OTel?" | Auto + manual instrumentation, exemplars, traceID in logs | `gateway/instrumentation.py` |
| "Onboarding?" | 15-min runbook: instrument → deploy → register → define SLO → verify | `docs/onboarding-guide.md` |
| "Training?" | 5 lessons: metrics, logs, traces, correlation, OTel basics | `training/` |
| "Observability as practice?" | Stakeholder briefs → dashboards → SLOs → runbooks → postmortems | `docs/stakeholder-briefs/`, `docs/runbooks/` |
| "Observability as practice?" | Stakeholder briefs → dashboards → SLOs → runbooks → postmortems | `docs/stakeholder-briefs/`, `docs/runbooks/` |

---

*Update per phase. Commit with `docs: update evidence map — <row> <dimension> to ✔`*