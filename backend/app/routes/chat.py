"""Chat endpoint — kicks off the travel agent upon user's input."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.deps import get_llm
from app.prompts.chat import CHAT_SYSTEM_PROMPT
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.llm import LLMService

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    llm: Annotated[LLMService, Depends(get_llm)],
) -> ChatResponse:
    """Call the LLM with the user's description of the desired trip."""
    response = await llm.call(request.text, CHAT_SYSTEM_PROMPT)
    return ChatResponse(response=response, tool_calls=[])
