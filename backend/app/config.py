from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).parent.parent.parent / ".env"


class Settings(BaseSettings):
    database_url: str
    groq_api_key: str = ""
    openai_api_key: str = ""
    langchain_api_key: str = ""
    cheap_model_name: str = "llama-3.1-8b-instant"
    strong_model_name: str = "gpt-4o"
    open_meteo_base_url: str = "https://api.open-meteo.com"

    model_config = SettingsConfigDict(env_file=_ENV_FILE)


settings = Settings()