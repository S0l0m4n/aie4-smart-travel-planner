"""Node factory functions for the sequential travel planning graph.

Each ``make_*`` function closes over the singletons it needs and returns
an async node function that LangGraph calls with the current state.
"""
from __future__ import annotations

import time
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.logging_config import get_logger
from app.retries import llm_retry
#from app.tools.classifier import DestinationFeatures, classify_travel_style
from app.tools.rag import retrieve_chunks

log = get_logger(__name__)


# ------------ Pydantic models for structured LLM output ----------------


class _EstimatedFeatures(BaseModel):
    hiking_score: float = Field(default=5.0, ge=1, le=10)
    beach_score: float = Field(default=5.0, ge=1, le=10)
    cultural_sites_score: float = Field(default=5.0, ge=1, le=10)
    nightlife_score: float = Field(default=5.0, ge=1, le=10)
    family_friendly_score: float = Field(default=5.0, ge=1, le=10)
    luxury_infrastructure_score: float = Field(default=5.0, ge=1, le=10)
    avg_accom_cost: float = Field(default=80.0, ge=0)
    avg_daily_expense: float = Field(default=50.0, ge=0)
    safety_score: float = Field(default=7.0, ge=1, le=10)
    remoteness_score: float = Field(default=5.0, ge=1, le=10)


class _ParseResult(BaseModel):
    budget_description: str = Field(default="unspecified")
    travel_dates: str = Field(default="unspecified")
    duration_days: int = Field(default=7, ge=1)
    interests: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    estimated_features: _EstimatedFeatures = Field(default_factory=_EstimatedFeatures)
    is_complete: bool = Field(
        default=False,
        description="True if travel dates/timing AND budget or duration are clearly stated",
    )


# ------------ Node factories --------------------------------------------


def make_parse_node(cheap_llm):
    structured_llm = cheap_llm.with_structured_output(_ParseResult)

    async def parse(state: dict[str, Any]) -> dict[str, Any]:
        messages = [
            SystemMessage(content=(
                "You are a travel assistant. Extract structured preferences from the user's travel request. "
                "Estimate what destination features they want on a scale of 1-10 "
                "(hiking_score, beach_score, cultural_sites_score, nightlife_score, "
                "family_friendly_score, luxury_infrastructure_score, safety_score, remoteness_score) "
                "and estimate avg_accom_cost and avg_daily_expense in USD. "
                "Set is_complete=true only if travel timing/dates AND budget or duration are mentioned."
            )),
            HumanMessage(content=state["user_message"]),
        ]
        try:
            async for attempt in llm_retry():
                with attempt:
                    result: _ParseResult = await structured_llm.ainvoke(messages)
            log.info("parse.complete", is_complete=result.is_complete)
            return {
                "parsed_preferences": result.model_dump(),
                "is_complete": result.is_complete,
                "tool_calls": state["tool_calls"] + [{
                    "tool": "parse",
                    "output": result.model_dump(exclude={"estimated_features"}),
                }],
            }
        except Exception as exc:
            log.error("parse.error", error=str(exc))
            return {
                "parsed_preferences": {},
                "is_complete": False,
                "tool_calls": state["tool_calls"] + [{"tool": "parse", "error": str(exc)}],
            }

    return parse


def make_ask_followup_node(cheap_llm):
    async def ask_followup(state: dict[str, Any]) -> dict[str, Any]:
        messages = [
            SystemMessage(content=(
                "You are a friendly travel assistant. The user's message is missing key details "
                "(travel dates/timing or budget). Ask a short, friendly question to get what's missing."
            )),
            HumanMessage(content=state["user_message"]),
        ]
        try:
            async for attempt in llm_retry():
                with attempt:
                    result = await cheap_llm.ainvoke(messages)
            return {"response": result.content}
        except Exception as exc:
            log.error("ask_followup.error", error=str(exc))
            return {"response": "Could you share when you'd like to travel and your approximate budget?"}

    return ask_followup


def make_classify_node(classifier):
    async def classify(state: dict[str, Any]) -> dict[str, Any]:
        t0 = time.monotonic()
        try:
            raw = state["parsed_preferences"].get("estimated_features", {})
            # Clip score fields to valid range in case the LLM drifts slightly.
            clipped = {
                k: max(1.0, min(10.0, float(v))) if k.endswith("_score") else float(v)
                for k, v in raw.items()
            }
            features = DestinationFeatures(**clipped)
            style = classify_travel_style(features, classifier)
            duration_ms = int((time.monotonic() - t0) * 1000)
            log.info("classify.complete", travel_style=style, duration_ms=duration_ms)
            return {
                "travel_style": style,
                "tool_calls": state["tool_calls"] + [{
                    "tool": "classifier",
                    "input": raw,
                    "output": style,
                    "duration_ms": duration_ms,
                }],
            }
        except Exception as exc:
            log.error("classify.error", error=str(exc))
            return {
                "travel_style": "Adventure",
                "tool_calls": state["tool_calls"] + [{"tool": "classifier", "error": str(exc)}],
            }

    return classify


def make_rewrite_node(cheap_llm):
    async def rewrite_query(state: dict[str, Any]) -> dict[str, Any]:
        prefs = state["parsed_preferences"]
        messages = [
            SystemMessage(content=(
                "Rewrite the user's travel request as a concise 1-2 sentence search query optimised "
                "for matching Wikivoyage destination articles. Focus on destination type, activities, "
                "and vibe — not specific city names."
            )),
            HumanMessage(content=(
                f"Request: {state['user_message']}\n"
                f"Travel style: {state['travel_style']}\n"
                f"Interests: {', '.join(prefs.get('interests', []))}\n"
                f"Constraints: {', '.join(prefs.get('constraints', []))}"
            )),
        ]
        try:
            async for attempt in llm_retry():
                with attempt:
                    result = await cheap_llm.ainvoke(messages)
            query = result.content.strip()
            log.info("rewrite_query.complete", query=query[:80])
            return {"rag_query": query}
        except Exception as exc:
            log.error("rewrite_query.error", error=str(exc))
            return {"rag_query": state["user_message"]}

    return rewrite_query


def make_retrieve_node(embed_model, session_factory):
    async def retrieve(state: dict[str, Any]) -> dict[str, Any]:
        t0 = time.monotonic()
        try:
            async with session_factory() as session:
                chunks = await retrieve_chunks(state["rag_query"], embed_model, session)
            duration_ms = int((time.monotonic() - t0) * 1000)
            destinations = list({c["destination_name"] for c in chunks})
            log.info("retrieve.complete", num_chunks=len(chunks), duration_ms=duration_ms)
            return {
                "retrieved_chunks": chunks,
                "tool_calls": state["tool_calls"] + [{
                    "tool": "rag",
                    "input": {"query": state["rag_query"]},
                    "output": {"num_chunks": len(chunks), "destinations": destinations},
                    "duration_ms": duration_ms,
                }],
            }
        except Exception as exc:
            log.error("retrieve.error", error=str(exc))
            return {
                "retrieved_chunks": [],
                "tool_calls": state["tool_calls"] + [{"tool": "rag", "error": str(exc)}],
            }

    return retrieve


def make_synthesize_node(strong_llm):
    async def synthesize(state: dict[str, Any]) -> dict[str, Any]:
        prefs = state["parsed_preferences"]
        chunks_text = "\n\n".join(
            f"[{c['destination_name']} — {c['source']}]\n{c['content']}"
            for c in state["retrieved_chunks"]
        )
        messages = [
            SystemMessage(content=(
                "You are an expert travel advisor. Using the user's preferences, their classified travel style, "
                "and the retrieved destination information below, write a detailed, practical recommendation. "
                "Include: top destination pick with reasoning, 1-2 alternatives, best time to visit, "
                "booking tips, and practical advice. Only recommend destinations from the retrieved context."
            )),
            HumanMessage(content=(
                f"User message: {state['user_message']}\n\n"
                f"Travel style: {state['travel_style']}\n"
                f"Budget: {prefs.get('budget_description', 'not specified')}\n"
                f"Dates: {prefs.get('travel_dates', 'not specified')}\n"
                f"Duration: {prefs.get('duration_days', '?')} days\n"
                f"Interests: {', '.join(prefs.get('interests', []))}\n"
                f"Constraints: {', '.join(prefs.get('constraints', []))}\n\n"
                f"Retrieved destination info:\n{chunks_text or 'No destinations retrieved.'}"
            )),
        ]
        try:
            async for attempt in llm_retry():
                with attempt:
                    result = await strong_llm.ainvoke(messages)
            log.info("synthesize.complete")
            return {"response": result.content}
        except Exception as exc:
            log.error("synthesize.error", error=str(exc))
            return {"response": f"Sorry, I encountered an error generating your recommendation: {exc}"}

    return synthesize
