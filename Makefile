COMPOSE := docker compose -f infra/docker-compose.yml

.PHONY: install up down langfuse worker migrate migration seed graph-seed ingest-runbooks eval eval-retrieval eval-verifier eval-ai training-data finetune-compare mcp-ai mcp-sentinel chaos lint format

install:  # sync all workspace deps
	uv sync --all-packages

up: install  # start datastores (Postgres, Redis, Qdrant, Neo4j) + run the API
	$(COMPOSE) up -d
	uv run uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --reload

down:  # stop datastores
	$(COMPOSE) down

langfuse:  # start Langfuse UI (http://localhost:3000, dev@sentinel.local / sentineldev)
	$(COMPOSE) --profile observability up -d langfuse-db langfuse

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

ingest-runbooks:  # embed runbooks into Qdrant
	uv run python -m scripts.ingest_runbooks

eval:  # graph root-cause eval (needs ANTHROPIC_API_KEY)
	uv run python -m scripts.eval graph

eval-retrieval:  # retrieval recall@3 eval
	uv run python -m scripts.eval retrieval

eval-verifier:  # verifier NLI accuracy eval
	uv run python -m scripts.eval verifier

eval-ai:  # AI-pipeline detection accuracy (headline metric)
	uv run python -m scripts.eval ai

training-data:  # build QLoRA training data: make training-data SYNTHETIC=200
	uv run python -m scripts.build_training_data $(SYNTHETIC)

finetune-compare:  # compare local fine-tuned model vs Claude (needs both served)
	uv run python experiments/finetune/compare.py

mcp-ai:  # run the AI-pipeline MCP server (stdio)
	uv run python apps/mcp-ai-pipeline/server.py

mcp-sentinel:  # run the Sentinel MCP server (HTTP, API-key protected)
	uv run python apps/mcp-sentinel/server.py

chaos:  # inject an AI fault: make chaos FAULT=embedding_drift
	uv run python -m scripts.chaos $(FAULT)

lint:  # ruff + mypy
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy

format:  # auto-format and fix
	uv run ruff format .
	uv run ruff check --fix .
