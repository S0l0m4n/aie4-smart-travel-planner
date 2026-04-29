"""LangGraph sequential travel planning graph.

Flow: parse → [is_complete?] → classify → rewrite_query → retrieve → synthesize
                     ↓ no
               ask_followup
"""
from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.agent.nodes import (
    make_ask_followup_node,
    make_classify_node,
    make_parse_node,
    make_retrieve_node,
    make_rewrite_node,
    make_synthesize_node,
)
from app.agent.state import AgentState


def build_graph(*, cheap_llm, strong_llm, classifier, embed_model, session_factory):
    graph = StateGraph(AgentState)

    graph.add_node("parse", make_parse_node(cheap_llm))
    graph.add_node("ask_followup", make_ask_followup_node(cheap_llm))
    graph.add_node("classify", make_classify_node(classifier))
    graph.add_node("rewrite_query", make_rewrite_node(cheap_llm))
    graph.add_node("retrieve", make_retrieve_node(embed_model, session_factory))
    graph.add_node("synthesize", make_synthesize_node(strong_llm))

    graph.add_edge(START, "parse")
    graph.add_conditional_edges(
        "parse",
        lambda state: "classify" if state["is_complete"] else "ask_followup",
    )
    graph.add_edge("ask_followup", END)
    graph.add_edge("classify", "rewrite_query")
    graph.add_edge("rewrite_query", "retrieve")
    graph.add_edge("retrieve", "synthesize")
    graph.add_edge("synthesize", END)

    return graph.compile()