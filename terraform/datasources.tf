# Observatory — Grafana Datasources
# ==================================
#
# Manages LGTM stack datasources in Grafana via Terraform.
# Replaces grafana/provisioning/datasources/datasources.yml for v0.6.0+.
#
# After terraform apply, remove the YAML provisioning file to avoid conflicts.
# Grafana provisioning YAML and Terraform can coexist, but Terraform takes
# ownership via import. YAML-provisioned resources become unmanaged.

resource "grafana_data_source" "mimir" {
  type = "prometheus"
  name = "Mimir"
  uid  = "mimir"

  url  = var.mimir_url
  is_default = false

  json_data_encoded = jsonencode({
    timeInterval    = "15s"
    queryTimeout    = "60s"
    httpMethod      = "POST"
  })

  secure_json_data_encoded = jsonencode({})

  lifecycle {
    prevent_destroy = false
  }
}

resource "grafana_data_source" "loki" {
  type = "loki"
  name = "Loki"
  uid  = "loki"

  url = var.loki_url

  json_data_encoded = jsonencode({
    maxLines = 1000
    derivedFields = [
      {
        name          = "traceID"
        matcherRegex  = "\"traceID\":\\s*\"([a-f0-9]{32})\""
        url           = "$${__value.raw}"
        datasourceUid = "tempo"
        matcherType   = "regex"
      }
    ]
  })
}

resource "grafana_data_source" "tempo" {
  type = "tempo"
  name = "Tempo"
  uid  = "tempo"

  url = var.tempo_url

  json_data_encoded = jsonencode({
    httpMethod = "GET"
    tracesToLogs = {
      datasourceUid = "loki"
      tags          = ["traceID"]
    }
    tracesToMetrics = {
      datasourceUid = "mimir"
      tags          = ["service.name"]
    }
    nodeGraph = {
      enabled = true
    }
  })
}
