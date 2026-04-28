import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.config import settings
from app.database import Base
import app.models  # noqa: F401 — registers models with Base.metadata
from app.routes.chat import router as chat_router

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("startup.begin")
    engine = create_async_engine(settings.database_url, echo=False)
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
    app.state.engine = engine
    app.state.session_factory = async_sessionmaker(engine, expire_on_commit=False)
    logger.info("startup.complete")
    yield
    logger.info("shutdown.begin")
    await engine.dispose()
    logger.info("shutdown.complete")


app = FastAPI(title="Smart Travel Planner", lifespan=lifespan)

app.include_router(chat_router, prefix="/api")
