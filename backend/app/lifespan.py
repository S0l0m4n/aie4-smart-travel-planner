"""FastAPI lifespan: build singletons on startup, dispose on shutdown."""
from __future__ import annotations

import os

# Silence Hugging Face network lookups
os.environ["HF_HUB_OFFLINE"] = "1"

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path

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

_CLASSIFIER_PATH = Path(__file__).parent / "ml" / "classifier.joblib"


@dataclass
class AppState:
    """Process-wide singletons attached to ``app.state.app_state``."""

    settings: Settings
    runner: TravelAgentRunner


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(level=settings.log_level, json_output=settings.log_json)
    log = get_logger(__name__)
    log.info("startup", cheap_model=settings.cheap_model_name, strong_model=settings.strong_model_name)

    engine = create_async_engine(settings.database_url, echo=False)
    try:
        async with engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await conn.run_sync(Base.metadata.create_all)
    except ConnectionRefusedError:
        log.error("Couldn't connect to the database, have you started the Postgres service?")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    classifier = joblib.load(_CLASSIFIER_PATH)
    embed_model = SentenceTransformer("all-MiniLM-L6-v2")

    cheap_llm = ChatGroq(api_key=settings.api_key, model=settings.cheap_model_name, temperature=0.3)
    strong_llm = ChatGroq(api_key=settings.api_key, model=settings.strong_model_name, temperature=0.3)

    runner = TravelAgentRunner(
        settings=settings,
        classifier=classifier,
        embed_model=embed_model,
        cheap_llm=cheap_llm,
        strong_llm=strong_llm,
        session_factory=session_factory,
    )

    app.state.app_state = AppState(settings=settings, runner=runner)

    log.info("startup.complete")
    try:
        yield
    finally:
        log.info("shutdown")
        await engine.dispose()
