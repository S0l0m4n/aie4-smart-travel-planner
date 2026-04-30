from __future__ import annotations

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000, description="User's travel question.")


class ChatResponse(BaseModel):
    response: str = Field(description="Agent's travel recommendation or follow-up question.")
    tool_calls: list[dict] = Field(description="Log of tools invoked during the agent run.")
