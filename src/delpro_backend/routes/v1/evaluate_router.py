"""WhatsApp webhook router for handling incoming messages and verification."""

import time

from fastapi import APIRouter, status
from fastapi.responses import Response

from delpro_backend.assistant.assistant_service import AssistantService
from delpro_backend.services.image_service import ImageService
from delpro_backend.services.rag_service import RAGService
from delpro_backend.services.vector_service import VectorService
from delpro_backend.services.whatsapp_service import WhatsAppService
from delpro_backend.utils.builders import get_embeddings, get_llm
from delpro_backend.utils.handle_errors import handle_errors
from delpro_backend.utils.logger import get_logger

logger_extra = {"component.name": "WebhookRouter", "component.version": "v1"}
logger = get_logger(__name__)

test_router = APIRouter(prefix="/test", tags=["test"])

# Initialize services with dependency injection
_embeddings = get_embeddings()
_llm = get_llm()

_vector_service = VectorService(embeddings=_embeddings)
_rag_service = RAGService(vector_service=_vector_service, embeddings=_embeddings)
_image_service = ImageService(embeddings=_embeddings)
_assistant_service = AssistantService(
    rag_service=_rag_service, llm=_llm, image_service=_image_service
)

whatsapp_service = WhatsAppService(assistant_service=_assistant_service)


@test_router.post("")
@handle_errors
async def receive_message(body: dict) -> Response:
    """POST /webhook - Handle incoming WhatsApp messages."""
    before = time.time()

    response = await whatsapp_service.handle_message(body)

    logger.info(f"Time elapsed: {time.time() - before}")

    return Response(content=response, status_code=status.HTTP_200_OK)
