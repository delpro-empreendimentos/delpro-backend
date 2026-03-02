"""WhatsApp webhook router for handling incoming messages and verification."""

import time
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse, Response

from delpro_backend.assistant.assistant_service import AssistantService
from delpro_backend.models.v1.exception_models import WebhookValidationError
from delpro_backend.services.broker_service import BrokerService
from delpro_backend.services.media_service import MediaService
from delpro_backend.services.rag_service import RAGService
from delpro_backend.services.vector_service import VectorService
from delpro_backend.services.whatsapp_service import WhatsAppService
from delpro_backend.utils.builders import get_embeddings, get_llm
from delpro_backend.utils.handle_errors import handle_errors
from delpro_backend.utils.logger import get_logger
from delpro_backend.utils.settings import settings

logger_extra = {"component.name": "WebhookRouter", "component.version": "v1"}
logger = get_logger(__name__)

whatsapp_router = APIRouter(prefix="/webhook", tags=["webhook"])

# Initialize services with dependency injection
_embeddings = get_embeddings()
_llm = get_llm()

_vector_service = VectorService(embeddings=_embeddings)
_rag_service = RAGService(vector_service=_vector_service, embeddings=_embeddings)
_media_service = MediaService(embeddings=_embeddings)
_assistant_service = AssistantService(
    rag_service=_rag_service, llm=_llm, media_service=_media_service
)

_broker_service = BrokerService()
whatsapp_service = WhatsAppService(
    assistant_service=_assistant_service, broker_service=_broker_service
)


@whatsapp_router.get("")
@handle_errors
async def validate_webhook(
    mode: str | None = Query(None, alias="hub.mode"),
    token: str | None = Query(None, alias="hub.verify_token"),
    challenge: str | None = Query(None, alias="hub.challenge"),
):
    """GET /webhook - Verify endpoint for WhatsApp."""
    if (mode is not None and token is not None) and (
        mode == "subscribe" and token == settings.WHATSAPP_ACCESS_TOKEN
    ):
        return JSONResponse(content=challenge or "", status_code=200)
    raise WebhookValidationError("Webhook verification failed")


@whatsapp_router.post("")
@handle_errors
async def receive_message(
    body: Annotated[dict, Depends(whatsapp_service.signature_required)],
) -> Response:
    """POST /webhook - Handle incoming WhatsApp messages."""
    before = time.time()

    await whatsapp_service.handle_message(body)

    logger.info(f"Time elapsed: {time.time() - before}")

    return Response(status_code=status.HTTP_200_OK)
