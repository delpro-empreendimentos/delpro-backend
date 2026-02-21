"""Centralized tool registry for the Delpro assistant.

All tools the agent has access to are defined here. Each tool must have
its description written in American English.
"""

import asyncio

from langchain_core.tools import tool

from delpro_backend.services.image_service import ImageService
from delpro_backend.services.rag_service import RAGService
from delpro_backend.services.whatsapp_api import send_message, upload_media
from delpro_backend.utils.logger import get_logger

logger = get_logger(__name__)


def build_tools(rag_service: RAGService, image_service: ImageService) -> list:
    """Build all agent tools with injected dependencies.

    Args:
        rag_service: Service for RAG context retrieval.
        image_service: Service for image storage and semantic search.

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

    @tool
    async def send_whatsapp_image(phone_number: str, descriptions: list[str]) -> str:
        """Search for images by description and send them to a WhatsApp user.

        Use this tool when the user requests images, photos, floor plans, or any
        visual material. Provide one natural-language description per image you want
        to find. The tool searches the image database semantically and sends the
        best match for each description.

        Args:
            phone_number: The recipient's WhatsApp phone number.
            descriptions: List of natural-language descriptions, one per desired image
                (e.g. ["piscina Edifício Solar", "planta 2 quartos"]).

        Returns:
            A summary of which images were sent and which had no match.
        """
        logger.info(
            "Executing tool send_whatsapp_image to %s, descriptions=%s",
            phone_number,
            descriptions,
        )

        # Search all descriptions in parallel
        search_results = await asyncio.gather(
            *[image_service.search_image_by_description(d) for d in descriptions]
        )

        not_found = []
        send_tasks = []

        for desc, img in zip(descriptions, search_results, strict=True):
            if img is None:
                not_found.append(desc)
            else:
                send_tasks.append(upload_media(
                        img.file_content, img.content_type, img.filename, phone_number=phone_number
                    ))

        if not send_tasks:
            return f"No matching images found for: {descriptions}"

        await asyncio.gather(*send_tasks)

        sent_count = len(send_tasks)
        parts = [f"Sent {sent_count} image(s) to {phone_number}."]
        if not_found:
            parts.append(f"Not found for: {not_found}")

        return " ".join(parts)

    return [search_knowledge_base, send_whatsapp_image]
