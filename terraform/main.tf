# Observatory — Terraform Grafana Provider Configuration
# ======================================================
#
# For v0.6.0 — ADR-009 Phase 2 migration from Provisioning YAML to Terraform.
#
# Provider auth: self-hosted OSS Grafana, API key or basic auth.
# In Docker Compose, Grafana allows anonymous Viewer access (demo only).
# Terraform uses the real admin credentials to manage resources.
#
# Usage:
#   cd terraform/
#   terraform init
#   terraform plan    # preview changes
#   terraform apply   # provision to Grafana
#
# Environment variables:
#   GRAFANA_URL      - Grafana instance URL (default: http://localhost:3000)
#   GRAFANA_USERNAME - Grafana admin username (default: admin)
#   GRAFANA_PASSWORD - Grafana admin password (default: admin)

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    grafana = {
      source  = "grafana/grafana"
      version = "~> 4.0"
    }
  }
}

provider "grafana" {
  url  = var.grafana_url
  auth = "${var.grafana_username}:${var.grafana_password}"
}
