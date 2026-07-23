# ADR-010: SLO Implementation via Sloth, and Terraform Migration Timing

**Status:** Accepted
**Date:** 2026-07-19
**Deciders:** Technical Lead, Claude Sonnet 5 (senior planner review)

## Context

Two related, previously-open questions needed resolution before v0.5.0 / v0.6.0 implementation:

1. How should Service Level Objectives (SLOs) with burn-rate alerting — a named job requirement — be implemented, given the stack is fully self-hosted (Docker Compose, no Grafana Cloud account)?
2. ADR-009 already decided dashboard provisioning moves to Terraform in "Phase 2," but left the timing open, anywhere between v0.6.0 and v2.0.0.

## Decision

**SLOs:** Implement via [Sloth](https://github.com/slok/sloth) (open source), generating Prometheus recording and multi-window multi-burn-rate alerting rules from a declarative spec (`sloth/gateway-slo.yaml`), deployed to Mimir's ruler via its local file storage backend.

**Terraform timing:** Land the ADR-009 Phase 2 migration at **v0.6.0**, not v2.0.0.

## Rationale

### Why Sloth, not the Grafana SLO app

Grafana's dedicated SLO application — guided UI, auto-generated dashboards and burn-rate alerts — is documented as a Grafana Cloud capability that a Grafana Cloud admin initializes. Grafana's own OSS-vs-Cloud comparison lists guided SLO management with auto-generated dashboards and multi-burn alerts as a Cloud differentiator, distinct from what Grafana OSS covers on its own (dashboards, alerting, data sources). This repo runs self-hosted OSS Grafana with no Cloud account anywhere in the stack. A Terraform `grafana_slo` resource does exist in the `grafana/grafana` provider, but its own setup documentation requires "a Grafana instance with the Grafana SLO app installed" — the same Cloud-gated dependency. Planning around that resource would stall at the point of actually applying it.

Sloth targets vanilla Prometheus rule format and implements the same underlying methodology the Grafana SLO app uses — the Google SRE Workbook's multi-window, multi-burn-rate alerting design — without requiring the app itself. It also generates a starter Grafana dashboard from the same spec. This is a stronger portfolio signal than the Cloud path: it demonstrates the burn-rate math is understood and implemented, not operated through someone else's setup wizard.

### Why file-based deployment, via Mimir's ruler

`mimir/mimir.yml` configures `ruler.storage.type: local`. Mimir's documentation states local ruler storage is explicitly read-only — it doesn't support the ruler's create/delete Configuration API — and that the ruler looks for tenant rule files at `<configured_path>/<TENANT_ID>/`. Practically: run `sloth generate -i sloth/gateway-slo.yaml -o gateway-slo-rules.yaml`, mount the output at `/data/rules/<tenant_id>/gateway-slo-rules.yaml` in the Mimir container. No API push, no additional service.

**Open action item:** `mimir.yml` does not yet set `multitenancy_enabled` or `no_auth_tenant` explicitly. Mimir is multi-tenant by design; without `multitenancy_enabled: false`, requests may be expected to carry an `X-Scope-OrgID` header — including the ruler's own tenant-scoped rule lookups — which `alloy/config.river`'s remote_write block doesn't currently send. Set both explicitly in `mimir.yml` before v0.5.0, and confirm the resulting tenant ID before finalizing the rule-file mount path above.

### Why Terraform at v0.6.0, not v2.0.0

Terraform and Ansible are named, required skills on the target job posting, each listed twice. ADR-009 already decided the *what* — Phase 1 YAML, Phase 2 Terraform. This ADR decides the *when*. Shipping v1.0.0, the GitHub publication milestone, without Terraform present in the repo leaves an unforced gap against the specific role this portfolio targets. v0.6.0 is early enough to land before publication and late enough that there's real provisioned state — the v0.2.0 logs dashboard plus whatever v0.3.0–v0.5.0 add — worth importing rather than an empty datasource block.

One naming detail to verify before writing the `.tf` files: the Terraform Grafana provider manages dashboards, folders, and data sources as core resources compatible with self-hosted OSS Grafana, not just Cloud. Confirm the exact data-source resource identifier against the registry docs at implementation time — earlier drafts referenced `grafana_datasource`; current provider documentation and examples more commonly show `grafana_data_source`. A five-minute check against the registry avoids a `terraform plan` failure on a naming mismatch.

## Consequences

### Positive
- SLO implementation works entirely within the existing self-hosted stack — no new external account or paid tier
- Multi-window multi-burn-rate alerting is demonstrably implemented, not just clicked through a UI
- Terraform lands before the publication milestone, closing a named, twice-listed job-requirement gap
- Sloth's generated dashboard is a second, independently-sourced Grafana dashboard (alongside the hand-built provisioning JSON) worth a mention in the before/after case study

### Negative
- Sloth is an added build-time dependency (CLI binary or container image used to generate rules) — not a runtime service, but another tool the README's one-command setup needs to account for
- Local ruler storage is read-only with no Configuration API — rule changes require regenerating and redeploying files rather than a live API call. Acceptable for a portfolio repo; production would move to an object-storage ruler backend

### Neutral
- The `grafana_slo` Terraform resource remains available if a future iteration adds a licensed Grafana Cloud/Enterprise tier with the SLO app installed — this decision doesn't foreclose that path, it just doesn't depend on it now

## Alternatives Considered

1. **Grafana Cloud SLO app + Terraform `grafana_slo`** — Rejected: requires a Grafana Cloud account and the SLO app installed, neither of which exists in this self-hosted deployment; would block on infrastructure outside current scope.
2. **Hand-written Prometheus rules, no generator** — Rejected: Sloth standardizes multi-window multi-burn-rate math (multiple alert severities across multiple time windows per SLO); reimplementing it by hand is exactly the error-prone boilerplate Sloth exists to eliminate, and using a recognized tool for it is itself a legible skill signal.
3. **Defer Terraform to v2.0.0** — Rejected: leaves the GitHub-publication milestone (v1.0.0) without a named, twice-listed job requirement present anywhere in the repo.

## Open Follow-ups (not blocking this ADR, tracked for v0.5.0)

- Confirm whether `instrumentation.py`'s Resource object sets `deployment.environment` or the current `deployment.environment.name` semantic convention name — affects `alloy/config.river`'s label hint and this decision's assumption that the Sloth spec's label selectors will match real data.
- Confirm the HTTP status-code label name emitted by the metrics pipeline (`http_response_status_code` per current OTel HTTP semantic conventions) before relying on `sloth/gateway-slo.yaml`'s error-rate queries.

## References

- [Sloth](https://github.com/slok/sloth)
- [Google SRE Workbook — Multiwindow, Multi-Burn-Rate Alerts](https://sre.google/workbook/alerting-on-slos/#6-multiwindow-multi-burn-rate-alerts)
- [Grafana Mimir Ruler — local storage](https://grafana.com/docs/mimir/latest/references/architecture/components/ruler/)
- [Grafana SLO (Cloud) documentation](https://grafana.com/docs/grafana-cloud/alerting-and-irm/slo/)
- [Grafana Cloud vs Grafana OSS](https://grafana.com/oss-vs-cloud/)
- [Terraform Grafana provider — resources](https://registry.terraform.io/providers/grafana/grafana/latest/docs)
- [OpenTelemetry Deployment Environment semantic convention](https://opentelemetry.io/docs/specs/semconv/resource/deployment-environment/)
- ADR-003 (log label strategy), ADR-009 (dashboard provisioning phasing)
- DECISION_LOG.md, 2026-07-19
