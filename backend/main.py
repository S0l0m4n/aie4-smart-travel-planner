"""FastAPI entry point for the Smart Travel Planner backend."""
from __future__ import annotations

from fastapi import FastAPI

from app.lifespan import lifespan
from app.routes import chat, health

app = FastAPI(
    title="Smart Travel Planner",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(chat.router, prefix="/api")