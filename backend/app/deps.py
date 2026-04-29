"""FastAPI dependency providers wiring singletons to request handlers."""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from app.agent.runner import TravelAgentRunner
from app.config import Settings
from app.lifespan import AppState


def get_app_state(request: Request) -> AppState:
    return request.app.state.app_state


def get_settings_dep(state: Annotated[AppState, Depends(get_app_state)]) -> Settings:
    return state.settings


def get_runner(state: Annotated[AppState, Depends(get_app_state)]) -> TravelAgentRunner:
    return state.runner