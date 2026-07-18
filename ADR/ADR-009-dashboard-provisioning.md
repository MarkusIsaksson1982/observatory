# ADR-009: Dashboard Provisioning — Phase 1 = Grafana YAML, Phase 2+ = Terraform

**Status:** Accepted
**Date:** 2025-07-18
**Deciders:** Technical Lead, Implementation Engineer

## Context

We need to provision Grafana datasources and dashboards. Two approaches:

1. **Grafana Provisioning YAML** — Built-in, file-based, one-way apply
2. **Terraform Grafana Provider** — `grafana_dashboard`, `grafana_folder`, `grafana_datasource`, `grafana_alert_rule`, `grafana_slo` resources; plan/apply workflow, drift detection, versioned state

## Decision

**Phase 1:** Grafana Provisioning YAML only (datasources + 1 dashboard)
**Phase 2+:** Migrate to Terraform Grafana Provider for all resources

## Consequences

### Positive
- **Phase 1 velocity:** No Terraform learning curve; YAML is instant feedback in docker-compose
- **Phase 2+ rigor:** Dashboard-as-code with drift detection, PR review on dashboard changes, versioned state
- **Clean migration:** JSON sources stay in repo; Terraform imports them
- **Portfolio signal:** Shows both approaches with clear rationale

### Negative
- **Migration effort:** Phase 2 requires `terraform import` for existing resources
- **Dual maintenance** during transition (mitigated: short window)

### Neutral
- JSON dashboard definitions remain source of truth throughout

## Alternatives Considered

1. **Terraform from Day 1** — Rejected: adds Terraform complexity before signal flow is validated; "infrastructure first, observability second" violates Principle 3
2. **Provisioning YAML forever** — Rejected: no drift detection, no PR review on dashboards, no versioned state; doesn't demonstrate "Dashboard as Code" rigor

## References

- [Grafana Terraform Provider](https://registry.terraform.io/providers/grafana/grafana/latest/docs)
- [Grafana Provisioning](https://grafana.com/docs/grafana/latest/administration/provisioning/)
- PROJECT_CONSTITUTION.md Section 4 (ADR-006, ADR-007)
- Design Principle #5: Automation over manual steps