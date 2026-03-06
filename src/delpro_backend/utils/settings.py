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
    GEMINI_MODEL: str
    MAX_TOKENS: int
    LLM_TEMPERATURE: int

    # Chat History
    MAX_HISTORY_MESSAGES: int

    # RAG Configuration
    EMBEDDING_MODEL: str
    CHUNK_SIZE: int
    CHUNK_OVERLAP: int
    RAG_TOP_K: int
    MAX_FILE_SIZE_MB: int = 10

    DATABASE_URL: str

    # WhatsApp Configuration (optional - set in .env to enable)
    WHATSAPP_ACCESS_TOKEN: str
    WHATSAPP_PHONE_NUMBER_ID: str
    WHATSAPP_APP_SECRET: str
    WHATSAPP_API_VERSION: str
    WHATSAPP_VERIFY_TOKEN: str

    ALLOWED_FILE_TYPES: list[str] = ["application/pdf", "text/plain"]
    MAX_FILES_PER_UPLOAD: int = 5


settings = Settings()  # type: ignore
