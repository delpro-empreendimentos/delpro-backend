"""Singleton for Google Generative AI embeddings model."""

import threading

from langchain_google_genai import GoogleGenerativeAIEmbeddings

from delpro_backend.utils.settings import settings

_embeddings: GoogleGenerativeAIEmbeddings | None = None
_lock = threading.Lock()


def get_embeddings() -> GoogleGenerativeAIEmbeddings:
    """Return the singleton embeddings model instance.

    Returns:
        The configured embeddings model.
    """
    global _embeddings

    if _embeddings is None:
        with _lock:
            if _embeddings is None:
                _embeddings = GoogleGenerativeAIEmbeddings(
                    model=settings.EMBEDDING_MODEL,
                    api_key=settings.API_KEY,  # type:ignore
                )

    return _embeddings
