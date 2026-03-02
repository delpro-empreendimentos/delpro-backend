"""Centralized tool registry for the Delpro assistant.

All tools the agent has access to are defined here. Each tool must have
its description written in American English.
"""

import asyncio

from langchain_core.tools import tool

# from delpro_backend.services import whatsapp_api
from delpro_backend.services.media_service import MediaService
from delpro_backend.services.rag_service import RAGService
from delpro_backend.services.whatsapp_api import WhatsappAPI
from delpro_backend.utils.logger import get_logger

logger = get_logger(__name__)

whatsapp_api = WhatsappAPI()


def build_tools(rag_service: RAGService, media_service: MediaService) -> list:
    """Build all agent tools with injected dependencies.

    Args:
        rag_service: Service for RAG context retrieval.
        media_service: Service for media storage and semantic search.

    Returns:
        List of LangChain tools available to the agent.
    """

    @tool
    async def search_knowledge_base(query: str) -> str:
        """Search Delpro's knowledge base for company or property information.

        WHEN TO USE THIS TOOL:
        Only call this tool when the user's CURRENT message explicitly asks for specific
        information about Delpro or one of its developments. The query MUST be derived
        solely from the user's current message — NEVER from previous messages or the
        conversation history.

        DO NOT call this tool for:
            - Greetings or small talk (e.g., "oi", "olá", "tudo bem", "obrigado")
            - Generic questions not related to Delpro (e.g., "me fala sobre imóveis")
            - Acknowledgements or confirmations (e.g., "entendi", "ok", "certo")
            - Follow-up messages that do not introduce a new specific question
            - Any message where the current text alone does not indicate what Delpro
              information is being requested

        VALID QUERIES — the query argument MUST be one of the following formats exactly,
        replacing [Building Name] with the name mentioned by the user in their current message:
            - `# Delpro Sobre a empresa:`
            - `# Delpro Missao, visao e valores:`
            - `# Delpro Visao:`
            - `# Delpro Produtos Lançados:`
            - `# Delpro Contato e localizacao:`
            - `# Delpro Historico e marcos importantes:`
            - `# Delpro Certificacoes e premios:`
            - `# Delpro Diferenciais competitivos:`
            - `# Delpro Informacoes financeiras e credibilidade:`
            - `# [Building Name] Visao geral do empreendimento:`
            - `# [Building Name] Localizacao e entorno:`
            - `# [Building Name] Tipos de unidades disponiveis:`
            - `# [Building Name] Tabela de precos e condicoes de pagamento:`
            - `# [Building Name] Areas comuns e infraestrutura de lazer:`
            - `# [Building Name] Acabamentos e especificacoes tecnicas:`
            - `# [Building Name] Comissao e condicoes para corretores:`
            - `# [Building Name] Status da obra e cronograma:`
            - `# [Building Name] Diferenciais do empreendimento:`

        Queries outside this list are invalid and will return no useful result.

        If the user does not know the building name but provides identifying details
        (address, neighborhood, launch date), use those as the query instead.
        Example: "Bairro: Passo da Areia" or "Endereco: Av. Joao Wallig".

        Args:
            query: A single search string matching one of the VALID QUERIES above,
                   built from the user's current message only.

        Returns:
            Relevant information from the knowledge base, or a message if nothing is found.
        """
        logger.info("Executing tool search_knowledge_base with query: %s", query)
        result = await rag_service.retrieve_context(query)
        logger.info("Retrieved content: %s", result)
        return result or "No relevant information found in the documents."

    @tool
    async def send_whatsapp_media(phone_number: str, queries: list[str]) -> str:
        """Search for media files by description and send them to a WhatsApp user.

        Use this tool when the user requests something that can contain visual information
        or documents, such as floor plan, sales table, building details, contracts, PDFs, etc.
        Identify based in the conversation all media that can fit in the user request,
        and build a short description one for each.

        POSSIBLE QUERIES:
            - `[Building name] fachada`
            - `[Building name] vista panoramica diurno`
            - `[Building name] vista panoramica noturno`
            - `[Building name] vista cobertura`
            - `[Building name] tabela de vendas`
            - `[Building name] folder`

        Replace `[Building Name]` for the building name specified by the user.

        Args:
            phone_number: Number of the user to send message (e.g.:+5551912345678)
            queries: query: Search terms in Portuguese, following strictly the list of
            `POSSIBLE QUERIES`.

        Returns:
            A summary of which media files were sent and which had no match.
        """
        logger.info(
            "Executing tool send_whatsapp_media to %s, queries=%s",
            phone_number,
            queries,
        )

        # Search all queries in parallel
        search_results = await asyncio.gather(
            *[media_service.search_media_by_description(d) for d in queries]
        )

        not_found = []
        send_tasks = []

        for desc, img in zip(queries, search_results, strict=True):
            if img is None:
                not_found.append(desc)
            else:
                send_tasks.append(
                    whatsapp_api.upload_media(
                        img.file_content, img.content_type, img.filename, phone_number=phone_number
                    )
                )

        if not send_tasks:
            return f"No matching media found for: {queries}"

        await asyncio.gather(*send_tasks)

        sent_count = len(send_tasks)
        parts = [f"Sent {sent_count} media file(s) to {phone_number}."]
        if not_found:
            parts.append(f"Not found for: {not_found}")

        return " ".join(parts)

    return [search_knowledge_base, send_whatsapp_media]
