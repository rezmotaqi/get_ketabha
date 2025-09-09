# =============================================================================
# Makefile for Telegram LibGen Bot Docker Management
# =============================================================================

.PHONY: help build up down restart logs shell test clean dev prod alpine

# Default target
help:
	@echo "Telegram LibGen Bot - Docker Management"
	@echo "======================================"
	@echo ""
	@echo "Available commands:"
	@echo "  make build     - Build all Docker images"
	@echo "  make up        - Start production services"
	@echo "  make dev       - Start development environment"
	@echo "  make prod      - Start production environment"
	@echo "  make alpine    - Start Alpine variant"
	@echo "  make down      - Stop all services"
	@echo "  make restart   - Restart all services"
	@echo "  make logs      - View logs"
	@echo "  make shell     - Open shell in container"
	@echo "  make test      - Run tests"
	@echo "  make clean     - Clean up Docker resources"
	@echo "  make status    - Show service status"
	@echo "  make health    - Check service health"
	@echo ""

# Build images
build:
	@echo "Building Docker images..."
	docker-compose build --no-cache

# Production deployment
up:
	@echo "Starting production services..."
	docker-compose up -d

# Development environment
dev:
	@echo "Starting development environment..."
	docker-compose --profile dev up -d

# Production environment
prod:
	@echo "Starting production environment..."
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Alpine variant
alpine:
	@echo "Starting Alpine variant..."
	docker-compose --profile alpine up -d

# Stop services
down:
	@echo "Stopping services..."
	docker-compose down

# Restart services
restart:
	@echo "Restarting services..."
	docker-compose restart

# View logs
logs:
	@echo "Viewing logs..."
	docker-compose logs -f libgen-bot

# Development logs
logs-dev:
	@echo "Viewing development logs..."
	docker-compose logs -f libgen-bot-dev

# Open shell in container
shell:
	@echo "Opening shell in container..."
	docker-compose exec libgen-bot /bin/bash

# Development shell
shell-dev:
	@echo "Opening development shell..."
	docker-compose exec libgen-bot-dev /bin/bash

# Run tests
test:
	@echo "Running tests..."
	docker-compose exec libgen-bot python -m pytest tests/ -v

# Simple search test
test-search:
	@echo "Testing search functionality..."
	docker-compose exec libgen-bot python simple_search.py "python programming"

# Show service status
status:
	@echo "Service status:"
	docker-compose ps

# Check service health
health:
	@echo "Checking service health..."
	docker-compose ps
	@echo ""
	@echo "Health check details:"
	docker inspect telegram-libgen-bot | jq '.[0].State.Health' 2>/dev/null || echo "Health check not available"

# Clean up Docker resources
clean:
	@echo "Cleaning up Docker resources..."
	docker-compose down -v
	docker system prune -f
	docker volume prune -f

# Full clean (including images)
clean-all:
	@echo "Full cleanup (including images)..."
	docker-compose down -v --rmi all
	docker system prune -a -f
	docker volume prune -f

# Update and restart
update:
	@echo "Updating and restarting services..."
	docker-compose pull
	docker-compose up -d

# Backup logs
backup-logs:
	@echo "Backing up logs..."
	mkdir -p backups
	tar -czf backups/logs-$(shell date +%Y%m%d-%H%M%S).tar.gz logs/

# Show resource usage
stats:
	@echo "Resource usage:"
	docker stats --no-stream

# Environment setup
setup:
	@echo "Setting up environment..."
	@if [ ! -f .env ]; then \
		echo "Creating .env file from template..."; \
		cp docker.env .env; \
		echo "Please edit .env file and set your TELEGRAM_BOT_TOKEN"; \
	else \
		echo ".env file already exists"; \
	fi

# Quick start
quickstart: setup up
	@echo "Quick start completed!"
	@echo "Check status with: make status"
	@echo "View logs with: make logs"

# Development quick start
dev-start: setup dev
	@echo "Development environment started!"
	@echo "Check status with: make status"
	@echo "View logs with: make logs-dev"

# Production quick start
prod-start: setup prod
	@echo "Production environment started!"
	@echo "Check status with: make status"
	@echo "View logs with: make logs"
