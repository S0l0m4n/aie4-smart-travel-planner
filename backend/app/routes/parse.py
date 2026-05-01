import logging
from typing import Annotated

from fastapi import APIRouter, Body, Depends

from app.deps import get_llm
from app.prompts.parse import PARSE_SYSTEM_PROMPT
from app.schemas.chat import ChatRequest
from app.schemas.classify import DestinationFeatures
from app.services.llm import LLMService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["parse"])

PARSE_EXAMPLES = {
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


async def parse_features(text: str, llm: LLMService) -> DestinationFeatures:
    response = await llm.call_structured(
        text,
        response_model=DestinationFeatures,
        system_prompt=PARSE_SYSTEM_PROMPT,
    )
    return DestinationFeatures.model_validate_json(response)


@router.post("/parse", response_model=DestinationFeatures)
async def parse(
        request: Annotated[ChatRequest, Body(openapi_examples=PARSE_EXAMPLES)],
        llm: Annotated[LLMService, Depends(get_llm)],
        ) -> DestinationFeatures:
    return await parse_features(request.text, llm)
