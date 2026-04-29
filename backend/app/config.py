"""Typed configuration loaded from the environment.

All configuration goes through ONE Settings class built on pydantic-settings.
Required keys are validated at startup — if API_KEY is empty the app refuses
to boot. No os.getenv scattered across modules.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    database_url: str = ""
    api_key: str = ""

    cheap_model_name: str = "llama-3.1-8b-instant"
    strong_model_name: str = "llama-3.3-70b-versatile"

    log_level: str = "INFO"
    log_json: bool = True

    @model_validator(mode="after")
    def _require_credentials(self) -> Settings:
        if not self.api_key:
            raise ValueError("API_KEY is required but not set.")
        if not self.database_url:
            raise ValueError("DATABASE_URL is required but not set.")
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached so every Depends(get_settings) returns the same instance."""
    return Settings()  # type: ignore[call-arg]