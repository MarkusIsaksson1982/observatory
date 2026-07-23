# Observatory — Grafana Dashboards
# =================================
#
# Imports existing JSON dashboard definitions from grafana/provisioning/dashboards/
# and manages them via Terraform. This gives PR-reviewable dashboard changes,
# drift detection, and versioned state (ADR-009 Phase 2).
#
# After terraform apply, remove the YAML dashboard provisioning to avoid conflicts.
#
# Dashboard inventory:
#   - service-health-red.json   → Service Health folder (6 RED panels)
#   - slo-burn-rate.json        → Reliability & SLO folder (9 SLO panels)
#   - system-overview.json      → Service Health folder (5 system panels)

resource "grafana_dashboard" "service_health_red" {
  config_json = file("${path.module}/../grafana/provisioning/dashboards/service-health-red.json")
  folder      = grafana_folder.service_health.id
  overwrite   = true

  lifecycle {
    prevent_destroy = false
  }
}

resource "grafana_dashboard" "slo_burn_rate" {
  config_json = file("${path.module}/../grafana/provisioning/dashboards/slo-burn-rate.json")
  folder      = grafana_folder.reliability.id
  overwrite   = true

  lifecycle {
    prevent_destroy = false
  }
}

resource "grafana_dashboard" "system_overview" {
  config_json = file("${path.module}/../grafana/provisioning/dashboards/system-overview.json")
  folder      = grafana_folder.service_health.id
  overwrite   = true
}
