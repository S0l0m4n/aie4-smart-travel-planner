"""FastAPI lifespan: build singletons on startup, dispose on shutdown."""
from __future__ import annotations

import os

# Silence Hugging Face network lookups
os.environ["HF_HUB_OFFLINE"] = "1"

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
import joblib
from fastapi import FastAPI
from langchain_groq import ChatGroq
from sentence_transformers import SentenceTransformer
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.agent.runner import TravelAgentRunner
from app.config import Settings, get_settings
from app.database import Base
from app.logging_config import configure_logging, get_logger
import app.models  # noqa: F401 — registers models with Base.metadata

from app.services.llm import LLMService
from app.tools.registry import ToolRegistry


@dataclass
class AppState:
    """Process-wide singletons attached to ``app.state.app_state``."""

    settings: Settings
    llm: LLMService
    registry: ToolRegistry


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
    log.info("startup", cheap_model=settings.cheap_model_name, strong_model=settings.strong_model_name)

    # Build collaborators
    llm = LLMService(settings)
    registry = ToolRegistry.build(settings)

    app.state.app_state = AppState(settings=settings, llm=llm, registry=registry)

    log.info("startup.complete")
    try:
        yield
    finally:
        # The `finally` block ensures we closes the HTTP pool even if there is
        # an unhandled error elsewhere
        log.info("shutdown")
        await llm.aclose()
