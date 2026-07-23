# Observatory — Grafana Alert Rules
# ===================================
#
# Unified alerting rules using Grafana's Provisioning API via Terraform.
# These complement Sloth-generated Prometheus recording/alerting rules
# (which target Mimir ruler) with Grafana-native alert rules that can
# use Grafana's notification channels directly.
#
# Dual alerting strategy:
#   - Sloth rules → Prometheus/Mimir ruler → burn-rate recording + multi-window alerts
#   - Grafana rules below → Grafana alerting engine → direct notification routing
#
# The Grafana rules below are simpler threshold-based alerts for operational
# dashboards. The Sloth-generated rules handle the SLO burn-rate logic.
#
# Metric source: Tempo metrics-generator → Mimir
#   traces_spanmetrics_calls_total{service, span_kind, status_code, ...}
#   traces_spanmetrics_duration_milliseconds_bucket{service, span_kind, le, ...}
#
# IMPORTANT: Label is "service" (not "service_name"). Value for gateway: "gateway".
#
# Resource type: grafana_rule_group (not grafana_alert_rule — provider v4.x)

resource "grafana_rule_group" "observatory_gateway" {
  name             = "observatory-gateway"
  folder_uid       = grafana_folder.reliability.uid
  interval_seconds = 60
  org_id           = "1"

  rule {
    name      = "Gateway High Error Rate"
    condition = "A"

    exec_err_state = "Error"
    no_data_state  = "OK"
    for            = "5m"

    annotations = {
      summary     = "Gateway error rate above 1% for 5 minutes"
      description = "The gateway service error rate has exceeded 1% for 5 minutes. Check the Service Health dashboard for details."
    }

    labels = {
      severity = "warning"
      team     = "platform"
      service  = "gateway"
    }

    data {
      ref_id = "A"

      datasource_uid = grafana_data_source.mimir.uid
      model = jsonencode({
        refId          = "A"
        expr = <<-EOT
          sum(rate(traces_spanmetrics_calls_total{service="gateway", span_kind="SPAN_KIND_SERVER", status_code="STATUS_CODE_ERROR"}[5m]))
          /
          sum(rate(traces_spanmetrics_calls_total{service="gateway", span_kind="SPAN_KIND_SERVER"}[5m]))
          * 100
        EOT
        legendFormat   = "Error rate %"
        intervalMs     = 15000
        maxDataPoints  = 400
      })

      relative_time_range {
        from = 300
        to   = 0
      }
    }
  }

  rule {
    name      = "Gateway High P99 Latency"
    condition = "A"

    exec_err_state = "Error"
    no_data_state  = "OK"
    for            = "5m"

    annotations = {
      summary     = "Gateway P99 latency above 500ms for 5 minutes"
      description = "The gateway service P99 latency has exceeded 500ms for 5 minutes."
    }

    labels = {
      severity = "warning"
      team     = "platform"
      service  = "gateway"
    }

    data {
      ref_id = "A"

      datasource_uid = grafana_data_source.mimir.uid
      model = jsonencode({
        refId          = "A"
        expr = <<-EOT
          histogram_quantile(0.99,
            sum(rate(traces_spanmetrics_duration_milliseconds_bucket{service="gateway", span_kind="SPAN_KIND_SERVER"}[5m])) by (le)
          )
        EOT
        legendFormat   = "P99 latency ms"
        intervalMs     = 15000
        maxDataPoints  = 400
      })

      relative_time_range {
        from = 300
        to   = 0
      }
    }
  }
}

# NOTE: Loki ingestion alert removed — Alloy self-monitoring scrape blocks
# in config.river have forward_to = [], so loki_ingester_* metrics are not
# wired to Mimir. Re-add when the scrape path is connected.
