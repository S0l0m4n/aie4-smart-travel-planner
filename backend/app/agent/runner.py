"""TravelAgentRunner — wraps the compiled LangGraph sequential graph.

One instance per process; created in lifespan and injected into routes
via Depends(get_runner). Mirrors the LangGraphAgentRunner pattern from
the reference project.
"""
from __future__ import annotations

from app.agent.graph import build_graph
from app.config import Settings
from app.logging_config import get_logger

log = get_logger(__name__)


class TravelAgentRunner:
    def __init__(
        self,
        settings: Settings,
        classifier,
        embed_model,
        cheap_llm,
        strong_llm,
        session_factory,
    ) -> None:
        self._settings = settings
        self._graph = build_graph(
            cheap_llm=cheap_llm,
            strong_llm=strong_llm,
            classifier=classifier,
            embed_model=embed_model,
            session_factory=session_factory,
        )

    async def run(self, *, message: str) -> dict:
        log.info("agent.run", message=message[:80])
        result = await self._graph.ainvoke({
            "user_message": message,
            "parsed_preferences": {},
            "is_complete": False,
            "travel_style": "",
            "rag_query": "",
            "retrieved_chunks": [],
            "response": "",
            "tool_calls": [],
        })
        log.info("agent.complete", travel_style=result.get("travel_style", ""))
        return {"response": result["response"], "tool_calls": result["tool_calls"]}
