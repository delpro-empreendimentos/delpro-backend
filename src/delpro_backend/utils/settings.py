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
    MAX_TOKENS_SUMMARY: int
    LLM_TEMPERATURE: int

    # Chat History
    MAX_HISTORY_MESSAGES: int = 5

    # RAG Configuration
    EMBEDDING_MODEL: str = "models/text-embedding-004"
    CHUNK_SIZE: int = 1200
    CHUNK_OVERLAP: int = 200
    RAG_TOP_K: int = 1  # Changed from 3 to 1 for faster responses
    MAX_FILE_SIZE_MB: int = 10
    ENABLE_RAG: bool = True
    BM25_WEIGHT: float = 0.3  # Keep for compatibility (not used in semantic-only)
    SEMANTIC_WEIGHT: float = 0.7  # Keep for compatibility (not used in semantic-only)

    DATABASE_URL: str

    LOG_LEVEL: str


settings = Settings()  # type: ignore
