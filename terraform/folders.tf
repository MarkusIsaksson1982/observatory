# Observatory — Grafana Folders
# ==============================
#
# Dashboard organization by genre (per Claude Sonnet 5's three-dashboard architecture):
#   - Service Health: Infra/RED for on-call engineers
#   - Reliability: SLO/error-budget for SLO owners
#   - Business KPIs: Conversion metrics for product managers

resource "grafana_folder" "service_health" {
  title = "Service Health"
}

resource "grafana_folder" "reliability" {
  title = "Reliability & SLO"
}

resource "grafana_folder" "business" {
  title = "Business KPIs"
}
