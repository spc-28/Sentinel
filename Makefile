COMPOSE := docker compose -f infra/docker-compose.yml
UV := uv

.DEFAULT_GOAL := help
.PHONY: help install infra up down worker lint format logs ps clean migrate migration seed

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "} {printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

install: ## Sync all workspace dependencies into .venv
	$(UV) sync --all-packages

infra: ## Start datastores only (Postgres, Redis, Qdrant)
	$(COMPOSE) up -d

up: install ## Start datastores, then run the API (foreground, with reload)
	$(COMPOSE) up -d
	$(UV) run uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --reload

worker: install ## Run the background worker (foreground)
	$(UV) run python -m apps.worker.main

migrate: ## Apply database migrations (alembic upgrade head)
	$(UV) run alembic upgrade head

migration: ## Autogenerate a migration: make migration NAME="message"
	$(UV) run alembic revision --autogenerate -m "$(NAME)"

seed: ## Insert sample services and runbooks
	$(UV) run python -m scripts.seed

down: ## Stop datastores
	$(COMPOSE) down

lint: ## Run ruff (lint + format check) and mypy
	$(UV) run ruff check .
	$(UV) run ruff format --check .
	$(UV) run mypy

format: ## Auto-format and auto-fix with ruff
	$(UV) run ruff format .
	$(UV) run ruff check --fix .

logs: ## Tail datastore logs
	$(COMPOSE) logs -f

ps: ## Show datastore status
	$(COMPOSE) ps

clean: ## Stop datastores and delete their volumes
	$(COMPOSE) down -v
