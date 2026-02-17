"""Centralized tool registry for the Delpro assistant.

All tools the agent has access to are defined here. Each tool must have
its description written in American English.
"""

from langchain_core.tools import tool

from delpro_backend.services.rag_service import RAGService
from delpro_backend.utils.logger import get_logger

logger = get_logger(__name__)


def build_tools(rag_service: RAGService) -> list:
    """Build all agent tools with injected dependencies.

    Args:
        rag_service: Service for RAG context retrieval.

    Returns:
        List of LangChain tools available to the agent.
    """

    @tool
    async def search_knowledge_base(query: str) -> str:
        """Search Delpro's knowledge base for property information.

        Use this tool to retrieve information about properties, prices, availability,
        amenities, locations, floor plans, and commercial data from Delpro's document store.
        This is your primary source of truth for answering questions about Delpro developments.

        Args:
            query: Search terms describing the desired information.

        Returns:
            Relevant information from the knowledge base, or a message if nothing is found.
        """
        logger.info("Executing tool search_knowledge_base with query: %s", query)
        result = await rag_service.retrieve_context(query)
        logger.info("Retrieved content: %s", result)
        return result or "No relevant information found in the documents."

    return [search_knowledge_base]
