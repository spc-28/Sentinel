# Sentinel

An AI SRE platform that investigates production incidents — receiving alerts,
running automated investigations across logs, metrics, traces and deploys, and
surfacing findings.

> **Status:** Part 1 — project scaffolding. A FastAPI server, a worker skeleton,
> and local datastores wired together and startable with one command.

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
| `make worker`  | Run the background worker                       |
| `make down`    | Stop datastores                                 |
| `make lint`    | Ruff lint + format check + mypy                |
| `make format`  | Auto-format and auto-fix                        |
| `make clean`   | Stop datastores and delete their volumes        |

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

`apps/mcp-sentinel` exposes Sentinel itself as **one MCP server** so you can ask it
to investigate from **Claude Code** (or Cursor) — investigate an incident without
leaving your editor. It runs over HTTP and is protected by an API key sent in the
`X-Sentinel-Key` header.

1. Start the stack and the MCP server:
   ```bash
   make up             # datastores + API (terminal 1)
   make worker         # investigation worker (terminal 2)
   make mcp-sentinel   # MCP server on http://127.0.0.1:8765/mcp (terminal 3)
   ```
2. This repo ships a project-scoped [`.mcp.json`](.mcp.json), so Claude Code picks up
   the `sentinel` server automatically when you open the project (approve it once when
   prompted). The API key defaults to `sentinel-dev-key`; set `MCP_API_KEY` in your
   `.env` to override it (the config reads `${MCP_API_KEY:-sentinel-dev-key}`).

   To register it yourself instead — globally or in another project:
   ```bash
   claude mcp add --transport http sentinel http://127.0.0.1:8765/mcp \
     --header "X-Sentinel-Key: sentinel-dev-key"
   ```
   Check it connected with `claude mcp list`.
3. In Claude Code, ask:
   > "What happened to checkout earlier? Investigate checkout-api latency."

   Claude calls `investigate`, Sentinel runs the five-agent graph, and the report
   comes back in the chat. Other tools: `get_investigation`, `recent_incidents`,
   `search_past_incidents`, `suggest_fix`.

Tools: `investigate` · `get_investigation` · `recent_incidents` ·
`search_past_incidents` · `suggest_fix`.
