# Observatory — Terraform Variables
# ==================================

variable "grafana_url" {
  description = "Grafana instance URL"
  type        = string
  default     = "http://localhost:3000"
}

variable "grafana_username" {
  description = "Grafana admin username"
  type        = string
  default     = "admin"
}

variable "grafana_password" {
  description = "Grafana admin password"
  type        = string
  default     = "admin"
  sensitive   = true
}

variable "environment" {
  description = "Deployment environment (local, staging, prod)"
  type        = string
  default     = "local"
}

variable "organization" {
  description = "Organization name for resource labels"
  type        = string
  default     = "observatory"
}

variable "mimir_url" {
  description = "Mimir/Prometheus-compatible URL for datasource"
  type        = string
  default     = "http://mimir:9009"
}

variable "loki_url" {
  description = "Loki URL for datasource"
  type        = string
  default     = "http://loki:3100"
}

variable "tempo_url" {
  description = "Tempo URL for datasource"
  type        = string
  default     = "http://tempo:3200"
}
