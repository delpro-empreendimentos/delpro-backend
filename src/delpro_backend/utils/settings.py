"""Settings module for the service."""

from dotenv import find_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings class for configuring the service."""

    model_config = SettingsConfigDict(env_file=find_dotenv(), env_file_encoding="utf-8", extra="ignore")

    # Whatsapp
    WPP_PHONE_ID: str
    WPP_TEST_NUMER: str
    WPP_TOKEN: str

    # Gemini LangChain
    API_KEY: str
    PROJECT_ID: str
    GEMINI_MODEL: str
    MAX_TOKENS: int
    LLM_TEMPERATURE: int

settings = Settings()  # type: ignore
