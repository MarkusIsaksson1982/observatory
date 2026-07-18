# Makefile for Observatory
# Commands: make up, make down, make logs, make validate, make lint

.PHONY: up down logs validate lint help

# Default target
help:
	@echo "Observatory - Observability Engineering Portfolio"
	@echo ""
	@echo "Commands:"
	@echo "  make up          - Start all services (Gateway + Alloy + LGTM)"
	@echo "  make down        - Stop and remove all containers"
	@echo "  make logs        - Follow all service logs"
	@echo "  make validate    - Health check all services"
	@echo "  make lint        - Run all linters"
	@echo ""

# Start all services
up:
	@echo "Starting Observatory stack..."
	docker compose up -d
	@echo "Waiting for services to be healthy..."
	@sleep 15
	@$(MAKE) validate
	@echo ""
	@echo "Observatory is ready!"
	@echo "  Grafana:    http://localhost:3000 (admin/admin)"
	@echo "  Gateway:    http://localhost:8000"
	@echo "  Alloy:      http://localhost:12347"
	@echo "  Mimir:      http://localhost:9009"
	@echo "  Tempo:      http://localhost:3200"
	@echo "  Loki:       http://localhost:3100"

# Stop and remove all containers
down:
	@echo "Stopping Observatory stack..."
	docker compose down -v

# Show logs
logs:
	docker compose logs -f

# Validate stack health
validate:
	@echo "Validating stack health..."
	@curl -sf http://localhost:9009/ready >/dev/null && echo "✓ Mimir ready" || (echo "✗ Mimir not ready"; exit 1)
	@curl -sf http://localhost:3100/ready >/dev/null && echo "✓ Loki ready" || (echo "✗ Loki not ready"; exit 1)
	@curl -sf http://localhost:3200/ready >/dev/null && echo "✓ Tempo ready" || (echo "✗ Tempo not ready"; exit 1)
	@curl -sf http://localhost:3000/api/health >/dev/null && echo "✓ Grafana ready" || (echo "✗ Grafana not ready"; exit 1)
	@curl -sf http://localhost:12347/-/ready >/dev/null && echo "✓ Alloy ready" || (echo "✗ Alloy not ready"; exit 1)
	@curl -sf http://localhost:8000/health >/dev/null && echo "✓ Gateway ready" || (echo "✗ Gateway not ready"; exit 1)
	@echo "All services healthy!"

# Lint all code
lint:
	@echo "Running linters..."
	@cd apps/gateway && uv run ruff check .
	@cd apps/gateway && uv run mypy .
	@docker run --rm -v ${PWD}:/workdir hadolint/hadolint hadolint apps/gateway/Dockerfile
	@docker run --rm -v ${PWD}:/workdir -w /workdir hashicorp/terraform:1.9 terraform fmt -check
	@docker run --rm -v ${PWD}:/workdir -w /workdir cytopia/yamllint yamllint .
	@echo "All linters passed!"