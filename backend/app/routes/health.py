"""Liveness check."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.config import Settings
from app.deps import get_settings_dep

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(settings: Annotated[Settings, Depends(get_settings_dep)]) -> dict:
    return {
        "status": "healthy",
        "llm_provider": settings.llm_provider,
        "cheap_model": settings.cheap_model_name,
        "strong_model": settings.strong_model_name,
    }
