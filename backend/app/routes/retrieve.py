from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_embed_model
from app.tools.rag import retrieve_chunks

router = APIRouter(tags=["debug"])


class RetrieveRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    k: int = Field(default=5, ge=1, le=20)


class ChunkResult(BaseModel):
    destination_name: str
    content: str
    source: str
    distance: float  # cosine distance — lower means more similar


class RetrieveResponse(BaseModel):
    query: str
    results: list[ChunkResult]


@router.post("/retrieve")
async def retrieve(
    req: RetrieveRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
    embed_model: Annotated[object, Depends(get_embed_model)],
) -> RetrieveResponse:
    chunks = await retrieve_chunks(req.query, embed_model, session, k=req.k)
    return RetrieveResponse(
        query=req.query,
        results=[ChunkResult(**c) for c in chunks],
    )
