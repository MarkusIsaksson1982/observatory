# Makefile for Observatory
# Core commands only - additional targets added when implemented

.PHONY: up down logs validate lint help

# Default target
help:
	@echo "Observatory - Observability Engineering Portfolio"
	@echo ""
	@echo "Commands:"
	@echo "  make up          - Start all services (Gateway + Alloy)"
	@echo "  make down        - Stop and remove all containers"
	@echo "  make logs        - Follow all service logs"
	@echo "  make validate    - Health check all services"
	@echo "  make lint        - Run all linters"
	@echo "  make help        - Show this help"

# Start all services
up:
	@echo "Starting Observatory stack..."
	docker compose up -d
	@echo "Waiting for services to be healthy..."
	@sleep 15
	@$(MAKE) validate
	@echo ""
	@echo "Observatory is ready!"
	@echo "  Alloy (OTLP):     http://localhost:4317 (gRPC) / http://localhost:4318 (HTTP)"
	@echo "  Alloy (metrics):  http://localhost:12345"
	@echo "  Gateway:          http://localhost:8000"

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
	@curl -sf http://localhost:12345/-/healthy >/dev/null && echo "  ✓ Alloy healthy" || (echo "  ✗ Alloy unhealthy"; exit 1)
	@curl -sf http://localhost:8000/health >/dev/null && echo "  ✓ Gateway healthy" || (echo "  ✗ Gateway unhealthy"; exit 1)
	@echo "All services healthy! ✓"

# Linting
lint:
	@echo "Running linters..."
	@cd apps/gateway && uv run ruff check .
	@cd apps/gateway && uv run mypy .
	@docker run --rm -v ${PWD}:/workdir hadolint/hadolint hadolint apps/gateway/Dockerfile
	@docker run --rm -v ${PWD}:/workdir -w /workdir hashicorp/terraform:1.9 terraform fmt -check
	@docker run --rm -v ${PWD}:/workdir -w /workdir cytopia/yamllint yamllint .
	@echo "All linters passed! ✓"

# Clean build artifacts
clean:
	@echo "Cleaning..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true