"""Typed configuration loaded from the environment.

All configuration goes through ONE Settings class built on pydantic-settings.
Required keys are validated at startup — if API_KEY is empty the app refuses
to boot. No os.getenv scattered across modules.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    """Strongly-typed configuration loaded from environment / ``.env`` file.

    Pydantic-settings turns environment variables into typed Python values and
    raises on unknown / malformed inputs.

    Every field below has a sensible default so the app can boot in dev mode
    just by setting the LLM provider, assuming the relevant key is defined.
    """
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        # "allow" so that provider-specific keys (GROQ_API_KEY, OPENAI_API_KEY,
        # etc.) land in model_extra without needing a declared field per provider.
        extra="allow",
        case_sensitive=False,
    )

    # --- provider ----------------------------------------------------
    # Which LLM provider drives chat + embeddings. The validator below
    # ensures the matching credential block is also populated.
    llm_provider: Literal["gemini", "openai", "groq"] = "groq"

    database_url: str = ""
    api_key: str = ""

    cheap_model_name: str = "llama-3.1-8b-instant"
    strong_model_name: str = "llama-3.3-70b-versatile"

    ml_model_path: Path = Path("app/ml/classifier.joblib")

    log_level: str = "INFO"
    log_json: bool = True

    @model_validator(mode="after")
    def _resolve_api_key(self) -> Settings:
        # pydantic-settings never injects .env values into os.environ, so
        # undeclared keys (e.g. GROQ_API_KEY) are read from model_extra.
        # case_sensitive=False means keys arrive lowercased.
        env_var = f"{self.llm_provider}_api_key"
        self.api_key = (self.model_extra or {}).get(env_var, "")
        if not self.api_key:
            raise ValueError(f"{env_var.upper()} is required but not set.")
        if not self.database_url:
            raise ValueError("DATABASE_URL is required but not set.")
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached so every Depends(get_settings) returns the same instance."""
    return Settings()  # type: ignore[call-arg]
