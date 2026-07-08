# Sentinel

An AI SRE platform that investigates production incidents — receiving alerts,
running automated investigations across logs, metrics, traces and deploys, and
surfacing findings.

When an alert fires (Grafana, Datadog, or a manual request), Sentinel runs a
five-agent investigation: it detects the affected service, correlates signals
across your telemetry, walks the service dependency graph to find likely blast
radius, and draws on past incidents and runbooks to explain what happened. Each
investigation produces a report with a root-cause hypothesis and a suggested fix,
delivered to the chat, email, or a GitHub issue.


## Requirements

- [uv](https://docs.astral.sh/uv/) (Python packaging) — Python 3.13 is installed automatically
- Docker + Docker Compose (for Postgres, Redis, Qdrant)
- `make`

## Quick start

```bash
cp .env.example .env          # local config (defaults work out of the box)
make up                       # start datastores + the API (http://localhost:8000)
```

Then, in another terminal:

```bash
curl localhost:8000/health    # -> {"status":"ok"}
curl localhost:8000/ready     # -> {"status":"ready", "checks": {...}} (200 when DB + Redis are up)
make worker                   # run the background worker
make down                     # stop datastores
```

## Common commands

| Command        | What it does                                   |
| -------------- | ---------------------------------------------- |
| `make up`      | Start datastores, then run the API (foreground)|
| `make infra`   | Start datastores only                          |
| `make worker`  | Run the background worker                      |
| `make down`    | Stop datastores                                |
| `make clean`   | Stop datastores and delete their volumes       |

## Layout

```
apps/
  api/              FastAPI server (alerts in, data out) — /health, /ready
  worker/           Background investigation worker
  mcp-sentinel/     MCP server exposing Sentinel to IDEs
  mcp-ai-pipeline/  MCP server for AI-health tools
  dashboard/        Web UI (built later)
packages/
  core/             Shared config, logging, DB models and schemas
  tools/            Plain-function access to logs, metrics, traces, deploys
  agents/           AI investigation logic
  rag/              Search over runbooks and logs
  graph/            Service dependency map
  memory/           Learning from past incidents
infra/         Docker Compose and deployment configs
scripts/       Setup and demo scripts
```

This is a [uv workspace](https://docs.astral.sh/uv/concepts/projects/workspaces/):
each app/package is a member; code is imported from the repo root
(e.g. `from packages.core.config import get_settings`).

## Connect Sentinel to Claude Code

`apps/mcp-sentinel` exposes Sentinel as **one MCP server**, so you can investigate
incidents from **Claude Code** (or Cursor) without leaving your editor. It runs over
HTTP, authenticated with an API key in the `X-Sentinel-Key` header.

**1. Start the stack** (one terminal each):

```bash
make up             # datastores + API
make worker         # investigation worker
make mcp-sentinel   # MCP server on http://127.0.0.1:8765/mcp
```

**2. Register the server.** This repo ships a project-scoped [`.mcp.json`](.mcp.json),
so Claude Code picks up the `sentinel` server automatically when you open the project
(approve it once when prompted).

To register it yourself instead — globally or in another project:

```bash
claude mcp add --transport http sentinel http://127.0.0.1:8765/mcp \
  --header "X-Sentinel-Key: sentinel-dev-key"
```

Verify it connected with `claude mcp list`.

**3. Ask Claude to investigate:**

> "What happened to checkout earlier? Investigate checkout-api latency."

Claude calls `investigate`, Sentinel runs the five-agent graph, and the report comes
back in the chat.

**API key:** defaults to `sentinel-dev-key`. Override it by setting `MCP_API_KEY` in
your `.env` (the config reads `${MCP_API_KEY:-sentinel-dev-key}`).



