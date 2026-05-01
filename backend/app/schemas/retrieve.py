from pydantic import BaseModel, Field
from typing import Literal


class RetrieveRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    k: int = Field(default=3, ge=1, le=20)


class ChunkResult(BaseModel):
    destination_name: str
    content: str
    source: str
    distance: float  # cosine distance — lower means more similar


class RetrieveResponse(BaseModel):
    query: str
    results: list[ChunkResult]
