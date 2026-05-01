import logging
from typing import Annotated

from fastapi import APIRouter, Body, Depends

from app.deps import get_classifier, get_llm
from app.ml.model import MLClassifier
from app.routes.parse import PARSE_EXAMPLES, parse_features
from app.schemas.chat import ChatRequest
from app.schemas.classify import ClassifyResponse
from app.services.llm import LLMService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["classify"])


@router.post("/classify", response_model=ClassifyResponse)
async def classify(
        request: Annotated[ChatRequest, Body(openapi_examples=PARSE_EXAMPLES)],
        llm: Annotated[LLMService, Depends(get_llm)],
        classifier: Annotated[MLClassifier, Depends(get_classifier)],
        ) -> ClassifyResponse:
    features = await parse_features(request.text, llm)
    return ClassifyResponse(label=classifier.predict(features))
