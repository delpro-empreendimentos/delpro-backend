"""Module for singleton to the llm instance.."""

import threading

from langchain_google_genai import GoogleGenerativeAI

from delpro_backend.utils.settings import settings

llm: GoogleGenerativeAI | None = None
_lock = threading.Lock()

LLM_INSTRUCTIONS = """
Voce é um assistente da empresa Delpro Empreendimentos que irá atender corretores de imoveis. Voce ira ser aplicado em
um contexto de funneling no WhatsApp. Seu objetivo é ir ao longo da conversa extraindo informacoes do corretor, a fim de
encontrar uma portunidade de negocio para vendas. Informacoes como, qual tipo de cliente ele tem, que produto o cliente
procura, e fazer um assessment se os produtos da Delpro podem STILL IN PROGRESS.
"""


def get_llm() -> GoogleGenerativeAI:
    """Docstring for get_llm.

    :rtype: GoogleGenerativeAI
    """
    global llm

    if llm is None:
        with _lock:
            llm = GoogleGenerativeAI(
                model=settings.GEMINI_MODEL,
                api_key=settings.API_KEY,
                temperature=settings.LLM_TEMPERATURE,
                instructions=LLM_INSTRUCTIONS,
                max_tokens=settings.MAX_TOKENS,
            )

    return llm
