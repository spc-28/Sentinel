"""The one MCP server: exposes Sentinel itself to AI clients (Claude Desktop, Cursor).

Textbook MCP: exposing a service across a boundary so any AI client can use it — an
engineer in their IDE can ask Sentinel to investigate without leaving the editor.
Thin by design: every tool just forwards to Sentinel's internal HTTP API.

Runs in network (HTTP) mode, protected by an API key in the ``X-Sentinel-Key`` header.
"""

from __future__ import annotations

import asyncio
import pathlib
import sys
from typing import Any

# The dir name has a hyphen (not importable), so add the repo root to the path.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import httpx  # noqa: E402
import structlog  # noqa: E402
import uvicorn  # noqa: E402
from mcp.server.fastmcp import FastMCP  # noqa: E402
from packages.core.config import get_settings  # noqa: E402
from starlette.middleware.base import BaseHTTPMiddleware  # noqa: E402
from starlette.requests import Request  # noqa: E402
from starlette.responses import JSONResponse  # noqa: E402
from starlette.types import ASGIApp  # noqa: E402

log = structlog.get_logger()
settings = get_settings()

mcp = FastMCP("sentinel", host=settings.mcp_host, port=settings.mcp_port)


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url=settings.sentinel_api_url, timeout=30.0)


@mcp.tool()
async def investigate(
    title: str, service: str = "unknown", severity: str = "high"
) -> dict[str, Any]:
    """Start an investigation for an alert and return the result once it's ready.

    Args:
        title: What's wrong, e.g. "checkout latency is high".
        service: The affected service (e.g. "checkout-api").
        severity: critical | high | medium | low | info.
    """
    async with _client() as client:
        response = await client.post(
            "/webhooks/alert", json={"title": title, "service": service, "severity": severity}
        )
        response.raise_for_status()
        data = response.json()
        alert_id = data["alert_id"]
        if not data.get("investigation_triggered"):
            return {
                "status": "grouped",
                "group_id": data.get("group_id"),
                "note": "Alert joined an existing incident group; no new investigation started.",
            }
        for _ in range(20):  # poll up to ~60s for the worker to finish
            await asyncio.sleep(3)
            result = await client.get(f"/investigations/by-alert/{alert_id}")
            if result.status_code == 200:
                detail = result.json()
                if detail["investigation"]["status"] in ("completed", "failed"):
                    return detail  # type: ignore[no-any-return]
    return {
        "status": "running",
        "alert_id": alert_id,
        "note": "Investigation still running; call get_investigation with the id shortly.",
    }


@mcp.tool()
async def get_investigation(investigation_id: str) -> dict[str, Any]:
    """Get the full result of an investigation (hypotheses + RCA report)."""
    async with _client() as client:
        response = await client.get(f"/investigations/{investigation_id}")
        response.raise_for_status()
        return response.json()  # type: ignore[no-any-return]


@mcp.tool()
async def recent_incidents(service: str | None = None, last_n_hours: int = 24) -> dict[str, Any]:
    """List recent incidents, optionally filtered by service."""
    params: dict[str, Any] = {"last_n_hours": last_n_hours}
    if service:
        params["service"] = service
    async with _client() as client:
        response = await client.get("/incidents", params=params)
        response.raise_for_status()
        return {"incidents": response.json()}


@mcp.tool()
async def search_past_incidents(question: str) -> dict[str, Any]:
    """Search past RCA reports for relevant history (root cause / summary / fix)."""
    async with _client() as client:
        response = await client.get("/investigations/search", params={"q": question})
        response.raise_for_status()
        return {"reports": response.json()}


@mcp.tool()
async def suggest_fix(investigation_id: str) -> dict[str, Any]:
    """Propose a fix for an investigation plus a draft revert PR."""
    async with _client() as client:
        response = await client.get(f"/investigations/{investigation_id}/suggest-fix")
        response.raise_for_status()
        return response.json()  # type: ignore[no-any-return]


class ApiKeyMiddleware(BaseHTTPMiddleware):
    """Reject requests without the shared secret in X-Sentinel-Key."""

    def __init__(self, app: ASGIApp, api_key: str) -> None:
        super().__init__(app)
        self._api_key = api_key

    async def dispatch(self, request: Request, call_next: Any) -> Any:
        if request.headers.get("x-sentinel-key") != self._api_key:
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        return await call_next(request)


def main() -> None:
    app = mcp.streamable_http_app()
    app.add_middleware(ApiKeyMiddleware, api_key=settings.mcp_api_key)
    log.info("mcp_sentinel.starting", host=settings.mcp_host, port=settings.mcp_port)
    uvicorn.run(app, host=settings.mcp_host, port=settings.mcp_port)


if __name__ == "__main__":
    main()
