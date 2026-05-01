from typing import Annotated

from fastapi import APIRouter, Body, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_embed_model
from app.rag.retriever import retrieve_chunks
from app.routes.parse import PARSE_EXAMPLES
from app.schemas.retrieve import RetrieveRequest, ChunkResult, RetrieveResponse

router = APIRouter(tags=["debug"])

RETRIEVE_EXAMPLES = {
    name: {"value": {"query": ex["value"]["text"], "k": 3}}
    for name, ex in PARSE_EXAMPLES.items()
}


@router.post("/retrieve")
async def retrieve(
    request: Annotated[RetrieveRequest, Body(openapi_examples=RETRIEVE_EXAMPLES)],
    session: Annotated[AsyncSession, Depends(get_db)],
    embed_model: Annotated[object, Depends(get_embed_model)],
) -> RetrieveResponse:
    chunks = await retrieve_chunks(request.query, embed_model, session, k=request.k)
    return RetrieveResponse(
        query=request.query,
        results=[ChunkResult(**c) for c in chunks],
    )
