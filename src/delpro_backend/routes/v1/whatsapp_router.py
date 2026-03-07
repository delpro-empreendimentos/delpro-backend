"""WhatsApp webhook router for handling incoming messages and verification."""

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Query, status
from fastapi.responses import PlainTextResponse, Response

from delpro_backend.assistant.assistant_service import AssistantService
from delpro_backend.models.v1.exception_models import WebhookValidationError
from delpro_backend.services.broker_service import BrokerService
from delpro_backend.services.media_service import MediaService
from delpro_backend.services.rag_service import RAGService
from delpro_backend.services.vector_service import VectorService
from delpro_backend.services.webhook_preprocessing_service import WebhookPreProcessingService
from delpro_backend.services.whatsapp_api import WhatsappAPI
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
whatsapp_api = WhatsappAPI()
whatsapp_service = WhatsAppService(
    assistant_service=_assistant_service, broker_service=_broker_service, whatsapp_api=whatsapp_api
)
preprocessing_service = WebhookPreProcessingService(
    whatsapp_api=whatsapp_api, whatsapp_service=whatsapp_service
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
        mode == "subscribe" and token == settings.WHATSAPP_VERIFY_TOKEN
    ):
        return PlainTextResponse(content=challenge or "", status_code=200)
    raise WebhookValidationError("Webhook verification failed")


@whatsapp_router.post("")
@handle_errors
async def receive_message(
    background_tasks: BackgroundTasks,
    body: Annotated[dict, Depends(whatsapp_service.signature_required)],
) -> Response:
    """POST /webhook - Handle incoming WhatsApp messages."""
    return await preprocessing_service.process(body, background_tasks)


@whatsapp_router.post("/dev")
async def receive_dev_message(
    background_tasks: BackgroundTasks,
    body: dict,
    x_dev_token: Annotated[str | None, Header()] = None,
) -> Response:
    """POST /webhook/dev - Receives forwarded messages from cloud for local debugging."""
    if not settings.DEV_INTERNAL_TOKEN or x_dev_token != settings.DEV_INTERNAL_TOKEN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    return await preprocessing_service.process_dev(body, background_tasks)
