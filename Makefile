COMPOSE := docker compose -f infra/docker-compose.yml

.PHONY: install up down worker migrate migration seed graph-seed eval lint format

install:  # sync all workspace deps
	uv sync --all-packages

up: install  # start datastores (Postgres, Redis, Qdrant, Neo4j) + run the API
	$(COMPOSE) up -d
	uv run uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --reload

down:  # stop datastores
	$(COMPOSE) down

worker: install  # run the background worker
	uv run python -m apps.worker.main

migrate:  # apply migrations
	uv run alembic upgrade head

migration:  # create a migration: make migration NAME="message"
	uv run alembic revision --autogenerate -m "$(NAME)"

seed:  # insert sample services and runbooks
	uv run python -m scripts.seed

graph-seed:  # seed the Neo4j dependency map
	uv run python -m scripts.seed_graph

eval:  # run the eval harness over docs/eval/cases.jsonl
	uv run python -m scripts.eval

lint:  # ruff + mypy
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy

format:  # auto-format and fix
	uv run ruff format .
	uv run ruff check --fix .
