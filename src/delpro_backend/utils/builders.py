"""Module for singleton to the chat LLM instance."""

import threading

from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

from delpro_backend.utils.settings import settings

_llm: ChatGoogleGenerativeAI | None = None
_lock = threading.Lock()
_embeddings: GoogleGenerativeAIEmbeddings | None = None
_embeddings_lock = threading.Lock()


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
