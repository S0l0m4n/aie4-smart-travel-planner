from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).parent.parent.parent / ".env"


class Settings(BaseSettings):
    database_url: str
    api_key: str
    langchain_api_key: str = ""
    cheap_model_name: str = "llama-3.1-8b-instant"
    strong_model_name: str = "llama-3.3-70b-versatile"
    open_meteo_base_url: str = "https://api.open-meteo.com"

    # Also look in the env file for env variables
    model_config = SettingsConfigDict(env_file=_ENV_FILE)


settings = Settings()
