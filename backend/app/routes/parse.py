import json
import logging
import time

from fastapi import APIRouter, Body, Depends, HTTPException
from typing import Annotated

from app.deps import get_llm
from app.prompts.parse import PARSE_SYSTEM_PROMPT
from app.schemas.chat import ChatRequest
from app.schemas.classify import DestinationFeatures
from app.services.llm import LLMService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["parse"])

EXAMPLES = {
    "beach_holiday": {
        "value": {
            "text": "I want to go somewhere cheap, a bit isolated and with "
                    "some nice surf."
        },
    },
    "mountain_trek": {
        "value": {
            "text": "I want to go on an intense hike in the mountains with "
                    "awesome scenic views, off the beaten path."
        },
    },
    "five_star_luxury": {
        "value": {
            "text": "I want to stay in a five-star hotel and rub shoulders "
                    "with the rich and famous"
        },
    },
}

@router.post("/parse", response_model=DestinationFeatures)
async def parse(
        request: Annotated[ChatRequest, Body(openapi_examples=EXAMPLES)],
        llm: Annotated[LLMService, Depends(get_llm)],
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
    response = await llm.call_structured(
        request.text,
        response_model=DestinationFeatures,
        system_prompt=PARSE_SYSTEM_PROMPT,
    )

    return DestinationFeatures.model_validate_json(response)
