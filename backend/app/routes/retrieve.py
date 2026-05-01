from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_embed_model
from app.rag.retriever import retrieve_chunks
from app.schemas.retrieve import RetrieveRequest, ChunkResult, RetrieveResponse

router = APIRouter(tags=["debug"])


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
