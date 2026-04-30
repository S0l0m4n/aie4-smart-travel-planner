import json
import logging
import time

from fastapi import APIRouter, HTTPException, Depends
from typing import Annotated

from app.deps import get_llm
from app.prompts.parse import PARSE_SYSTEM_PROMPT
from app.schemas.chat import ChatRequest
from app.schemas.classify import DestinationFeatures
from app.services.llm import LLMService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["parse"])


@router.post("/parse", response_model=DestinationFeatures)
async def parse(
        request: ChatRequest,
        llm: Annotated[LLMService, Depends(get_llm)]
        ) -> DestinationFeatures:
    """Extract the features specifying the user's description of their ideal
    travel destination.

    Args:
        request: User input text (`ChatRequest` type)
        llm: Injected shared `LLMService`

    Returns:
        A `DestinationFeatures` object estimating the feature scores for the
        user's described location.
    """
    response = await llm.call(
        request.text,
        system_prompt=PARSE_SYSTEM_PROMPT,
        response_model=DestinationFeatures,
    )

    return DestinationFeatures.model_validate_json(response)
