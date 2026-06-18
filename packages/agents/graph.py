"""LangGraph wiring of the five-agent team, with a Postgres checkpointer.

Flow:
    START → detector
    detector → reporter            (false alarm: stop early)
    detector → investigator        (real incident)
    investigator → hypothesizer → verifier
    verifier → reporter            (a hypothesis holds up, or retries exhausted)
    verifier → investigator        (nothing holds up: gather more — max 2 retries)
    reporter → END
"""

from __future__ import annotations

from typing import Any, cast

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import END, START, StateGraph

from packages.agents.nodes.detector import detect
from packages.agents.nodes.hypothesizer import hypothesize
from packages.agents.nodes.investigator import investigate
from packages.agents.nodes.reporter import report
from packages.agents.nodes.verifier import verify
from packages.agents.state import GraphState, initial_state
from packages.core.config import get_settings

# Initial verify + up to 2 investigator retries.
_MAX_VERIFY_ATTEMPTS = 3


def _route_after_detector(state: GraphState) -> str:
    return "investigator" if state.get("is_real", True) else "reporter"


def _route_after_verifier(state: GraphState) -> str:
    supported = any(v.verdict == "supported" for v in state.get("verified", []))
    if supported or state.get("verify_attempts", 0) >= _MAX_VERIFY_ATTEMPTS:
        return "reporter"
    return "investigator"


def build_graph() -> Any:  # StateGraph's generics are awkward to spell; treat as Any
    builder = StateGraph(GraphState)
    builder.add_node("detector", detect)
    builder.add_node("investigator", investigate)
    builder.add_node("hypothesizer", hypothesize)
    builder.add_node("verifier", verify)
    builder.add_node("reporter", report)

    builder.add_edge(START, "detector")
    builder.add_conditional_edges(
        "detector", _route_after_detector, {"investigator": "investigator", "reporter": "reporter"}
    )
    builder.add_edge("investigator", "hypothesizer")
    builder.add_edge("hypothesizer", "verifier")
    builder.add_conditional_edges(
        "verifier", _route_after_verifier, {"investigator": "investigator", "reporter": "reporter"}
    )
    builder.add_edge("reporter", END)
    return builder


async def run_graph(
    alert: dict[str, object], thread_id: str, *, resume: bool = False
) -> GraphState:
    """Run (or resume) the investigation graph for ``thread_id``.

    State is checkpointed in Postgres after each node, so passing ``resume=True``
    (with input ``None``) continues an interrupted run from its last checkpoint.
    """
    settings = get_settings()
    async with AsyncPostgresSaver.from_conn_string(settings.postgres_dsn) as saver:
        await saver.setup()
        graph = build_graph().compile(checkpointer=saver)
        config = {"configurable": {"thread_id": thread_id}}
        payload = None if resume else initial_state(alert)
        final = await graph.ainvoke(payload, config=config)
        return cast(GraphState, final)
