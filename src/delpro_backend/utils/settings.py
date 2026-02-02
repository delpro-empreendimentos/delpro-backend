"""Settings module for the service."""

from dotenv import find_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings class for configuring the service."""

    model_config = SettingsConfigDict(
        env_file=find_dotenv(), env_file_encoding="utf-8", extra="ignore"
    )

    # Gemini LangChain
    API_KEY: str
    PROJECT_ID: str
    GEMINI_MODEL: str
    MAX_TOKENS: int
    LLM_TEMPERATURE: int

    # Chat History
    MAX_HISTORY_MESSAGES: int = 5

    DATABASE_URL: str


settings = Settings()  # type: ignore
