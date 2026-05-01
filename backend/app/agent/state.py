from typing import TypedDict


class AgentState(TypedDict):
    user_message: str
    parsed_preferences: dict
    is_complete: bool
    travel_style: str
    rag_query: str
    retrieved_chunks: list[dict]
    response: str
    tool_calls: list[dict]
