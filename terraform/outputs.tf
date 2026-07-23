# Observatory — Terraform Outputs
# =================================

output "grafana_url" {
  description = "Grafana instance URL"
  value       = var.grafana_url
}

output "datasource_uids" {
  description = "UIDs of provisioned datasources"
  value = {
    mimir = grafana_data_source.mimir.uid
    loki  = grafana_data_source.loki.uid
    tempo = grafana_data_source.tempo.uid
  }
}

output "dashboard_uids" {
  description = "UIDs of provisioned dashboards"
  value = {
    service_health_red = grafana_dashboard.service_health_red.uid
    slo_burn_rate      = grafana_dashboard.slo_burn_rate.uid
    system_overview    = grafana_dashboard.system_overview.uid
  }
}

output "folder_uids" {
  description = "UIDs of dashboard folders"
  value = {
    service_health = grafana_folder.service_health.uid
    reliability    = grafana_folder.reliability.uid
    business       = grafana_folder.business.uid
  }
}
