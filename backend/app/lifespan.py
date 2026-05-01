"""FastAPI lifespan: build singletons on startup, dispose on shutdown."""
from __future__ import annotations

import os

# Silence Hugging Face network lookups — model must be pre-cached locally.
os.environ["HF_HUB_OFFLINE"] = "1"

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from fastapi import FastAPI

from sentence_transformers import SentenceTransformer
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import Settings, get_settings
from app.database import Base
from app.logging_config import configure_logging, get_logger
from app.ml.model import MLClassifier
from app.services.llm import LLMService
from app.tools.registry import ToolRegistry
import app.models  # noqa: F401 — registers models with Base.metadata


@dataclass
class AppState:
    """Process-wide singletons attached to ``app.state.app_state``."""

    settings: Settings
    llm: LLMService
    registry: ToolRegistry
    classifier: MLClassifier
    embed_model: SentenceTransformer


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup/shutdown context for the FastAPI application.

    Yields control back to FastAPI once initialisation is done; the code
    after the `yield` runs when the server is shutting down (e.g. SIGTERM
    in production, Ctrl-C locally).

    Args:
        app: The FastAPI application; we attach state to `app.state`.

    Yields:
        Nothing — the body of the contextmanager is the running app.
    """
    settings = get_settings()
    configure_logging(level=settings.log_level, json_output=settings.log_json)
    log = get_logger(__name__)
    log.info("startup", provider=settings.llm_provider, model=settings.model_name())

    engine = create_async_engine(settings.database_url, echo=False)
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
    # Attached directly to app.state so get_db can reach it via request.app.state.
    app.state.session_factory = async_sessionmaker(engine, expire_on_commit=False)

    # Build collaborators
    llm = LLMService(settings)
    registry = ToolRegistry.build(settings)
    classifier = MLClassifier(settings.ml_model_path)
    embed_model = SentenceTransformer("all-MiniLM-L6-v2")

    app.state.app_state = AppState(
        settings=settings,
        llm=llm,
        registry=registry,
        classifier=classifier,
        embed_model=embed_model,
    )

    log.info("startup.complete")
    try:
        yield
    finally:
        # The `finally` block ensures we close the HTTP pool and DB engine
        # even if there is an unhandled error elsewhere.
        log.info("shutdown")
        await llm.aclose()
        await engine.dispose()