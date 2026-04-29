"""Chat endpoint — runs the sequential travel agent."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.agent.runner import TravelAgentRunner
from app.deps import get_runner
from app.schemas.chat import ChatRequest, ChatResponse

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    runner: Annotated[TravelAgentRunner, Depends(get_runner)],
) -> ChatResponse:
    result = await runner.run(message=body.message)
    return ChatResponse(**result)