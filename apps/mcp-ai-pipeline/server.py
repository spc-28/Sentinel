"""MCP server exposing Sentinel's AI-pipeline health checks to any AI client.

AI-pipeline health is exactly the kind of tool other AI clients want to call — an
engineer in Cursor/Claude Desktop asking "is my RAG healthy?". That's a real
boundary, so MCP earns its place here (unlike internal data access = plain functions).

Run from Claude Desktop with:
    command: uv
    args: ["run", "--directory", "/path/to/sentinel", "python",
           "apps/mcp-ai-pipeline/server.py"]
"""

from __future__ import annotations

import pathlib
import sys
from typing import Any

# The dir name has a hyphen (not importable), so add the repo root to the path.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from mcp.server.fastmcp import FastMCP  # noqa: E402
from packages.agents.ai_pipeline import detectors  # noqa: E402

mcp = FastMCP("sentinel-ai-pipeline")


@mcp.tool()
async def check_index_health(index_name: str = "runbooks") -> dict[str, Any]:
    """Overall health of a vector index: point count and embedding drift."""
    return (await detectors.check_index_health(index_name)).model_dump()


@mcp.tool()
async def check_embedding_drift(
    index_name: str = "runbooks", last_n_hours: int = 24
) -> dict[str, Any]:
    """Detect embedding drift for an index (Wasserstein distance vs a baseline)."""
    return (await detectors.check_embedding_drift(index_name, last_n_hours)).model_dump()


@mcp.tool()
async def check_rag_quality(index_name: str = "runbooks") -> dict[str, Any]:
    """Score RAG answer faithfulness (DeBERTa-MNLI) and flag quality drops."""
    return (await detectors.check_rag_quality(index_name)).model_dump()


@mcp.tool()
async def get_ai_cost(service: str = "checkout-api", last_n_hours: int = 24) -> dict[str, Any]:
    """Hourly AI spend for a service and whether the latest hour spiked."""
    return (await detectors.get_ai_cost(service, last_n_hours)).model_dump()


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
