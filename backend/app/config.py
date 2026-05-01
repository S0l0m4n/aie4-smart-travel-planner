"""Typed configuration loaded from the environment.

All configuration goes through ONE Settings class built on pydantic-settings.
Required keys are validated at startup — if API_KEY is empty the app refuses
to boot. No os.getenv scattered across modules.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_ENV_FILE = PROJECT_ROOT / ".env"


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

    gemini_model: str = "gemini-2.5-flash"
    openai_model: str = "gpt-4o-mini"
    groq_model: str = "openai/gpt-oss-20b"

    database_url: str = ""
    api_key: str = ""

    cheap_model_name: str = "llama-3.1-8b-instant"
    strong_model_name: str = "llama-3.3-70b-versatile"

    # --- ML model ----------------------------------------------------
    ml_model_path: Path = PROJECT_ROOT / "backend" / "app" / "ml" / "classifier.joblib"

    # --- runtime -----------------------------------------------------
    llm_request_timeout_seconds: int = 10

    # --- safety ------------------------------------------------------

    # --- observability -----------------------------------------------
    log_level: str = "INFO"
    log_json: bool = True

    # --- caching -----------------------------------------------------

    # --- storage paths -----------------------------------------------
    # Defaults are derived from PROJECT_ROOT so the app finds its data
    # files no matter what the current working directory is.
    knowledge_data_path: Path = Field(
        default=PROJECT_ROOT / "data" / "raw_wikivoyage",
        description="Path to the scraped data from Wikivoyage on various "
        "destinations, stored as text files."
    )

    # -----------------------------------------------------------------

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

    def model_name(self) -> str:
        """Return the provider-specific model identifier currently in use.

        Returns:
            The model name for OpenAI / Gemini / Groq.
        """
        return {
            "gemini": self.gemini_model,
            "openai": self.openai_model,
            "groq": self.groq_model,
        }[self.llm_provider]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached so every Depends(get_settings) returns the same instance."""
    return Settings()  # type: ignore[call-arg]
