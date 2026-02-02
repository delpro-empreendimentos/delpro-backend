"""Module for singleton to the chat LLM instance."""

import threading

from langchain_google_genai import ChatGoogleGenerativeAI

from delpro_backend.utils.settings import settings

_llm: ChatGoogleGenerativeAI | None = None
_lock = threading.Lock()


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
