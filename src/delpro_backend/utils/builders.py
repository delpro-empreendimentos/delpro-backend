"""Module for singleton to the chat LLM instance."""

import threading

import redis.asyncio as aioredis
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

from delpro_backend.utils.settings import settings

_llm: ChatGoogleGenerativeAI | None = None
_summary_llm: ChatGoogleGenerativeAI | None = None
_lock = threading.Lock()
_summary_lock = threading.Lock()
_embeddings: GoogleGenerativeAIEmbeddings | None = None
_embeddings_lock = threading.Lock()
_redis_client: aioredis.Redis | None = None
_redis_lock = threading.Lock()


def get_llm() -> ChatGoogleGenerativeAI:
    """Return the singleton ChatGoogleGenerativeAI instance.

    Returns:
        The configured chat model instance.
    """
    global _llm

    if _llm is None:
        with _lock:
            if _llm is None:
                _llm = ChatGoogleGenerativeAI(
                    model=settings.GEMINI_MODEL,
                    api_key=settings.API_KEY,
                    temperature=settings.LLM_TEMPERATURE,
                    max_tokens=settings.MAX_TOKENS,
                )

    return _llm


def get_summary_llm() -> ChatGoogleGenerativeAI:
    """Return the singleton ChatGoogleGenerativeAI instance for summarization.

    Uses MAX_TOKENS_SUMMARY instead of MAX_TOKENS to allow longer summaries.

    Returns:
        The configured chat model instance for summarization.
    """
    global _summary_llm

    if _summary_llm is None:
        with _summary_lock:
            if _summary_llm is None:
                _summary_llm = ChatGoogleGenerativeAI(
                    model=settings.GEMINI_MODEL,
                    api_key=settings.API_KEY,
                    temperature=settings.LLM_TEMPERATURE,
                    max_tokens=settings.MAX_TOKENS_SUMMARY,
                )

    return _summary_llm


def get_embeddings() -> GoogleGenerativeAIEmbeddings:
    """Return the singleton embeddings model instance.

    Returns:
        The configured embeddings model.
    """
    global _embeddings

    if _embeddings is None:
        with _embeddings_lock:
            if _embeddings is None:
                _embeddings = GoogleGenerativeAIEmbeddings(
                    model=settings.EMBEDDING_MODEL,
                    api_key=settings.API_KEY,  # type:ignore
                )

    return _embeddings


def get_redis() -> aioredis.Redis:
    """Return the singleton async Redis client.

    Returns:
        The configured async Redis client.
    """
    global _redis_client

    if _redis_client is None:
        with _redis_lock:
            if _redis_client is None:
                _redis_client = aioredis.from_url(settings.REDIS_URL)

    return _redis_client
