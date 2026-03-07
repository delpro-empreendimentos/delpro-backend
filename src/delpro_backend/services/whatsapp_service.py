"""WhatsApp Service for sending and processing messages."""

import hashlib
import hmac
import json

from fastapi import HTTPException, Request

from delpro_backend.assistant.assistant_service import AssistantService
from delpro_backend.services.broker_service import BrokerService
from delpro_backend.services.whatsapp_api import WhatsappAPI
from delpro_backend.utils.logger import get_logger
from delpro_backend.utils.settings import settings

logger_extra = {"component.name": "WhatsappService", "component.version": "v1"}
logger = get_logger(__name__)


class WhatsAppService:
    """Service for WhatsApp message operations."""

    def __init__(
        self,
        assistant_service: AssistantService,
        broker_service: BrokerService,
        whatsapp_api: WhatsappAPI,
    ):
        """WhatsApp service class module."""
        self._assistant_service = assistant_service
        self._broker_service = broker_service
        self.whatsapp_api = whatsapp_api

    async def signature_required(self, request: Request) -> dict:
        """Dependency to ensure incoming requests are valid and signed correctly.

        Equivalent to Flask's @signature_required decorator.
        """
        signature = request.headers.get("X-Hub-Signature-256", "")[7:]
        body = await request.body()
        payload = body.decode("utf-8")

        expected_signature = hmac.new(
            bytes(settings.WHATSAPP_APP_SECRET, "latin-1"),
            msg=payload.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(expected_signature, signature):
            logger.info("Signature verification failed!", extra=logger_extra)
            raise HTTPException(status_code=403, detail="Invalid signature")

        return json.loads(payload)

    async def handle_message(
        self, text: str, sender_phone_number: str, sender_name: str
    ):
        """Process an incoming WhatsApp message and send a response.

        Args:
            message_id: The unique identifier of the message.
            text: The message text content.
            sender_phone_number: The phone number of the sender.
            sender_name: The name of the sender.

        Returns:
            None for status updates/duplicates (acknowledged but not processed),
            or response dict for processed messages.
        """
        if text == "/reset memory":
            await self._assistant_service.clear_history(sender_phone_number)
            await self.whatsapp_api.send_message(to=sender_phone_number, text="Memória resetada.")
            return

        logger.info(
            "Processing message '%s' from %s (%s)",
            text,
            sender_name,
            sender_phone_number,
            extra=logger_extra,
        )

        response_text = await self._assistant_service.chat(
            sender_phone_number=sender_phone_number,
            user_message=text,
            user_name=sender_name,
        )

        logger.info(
            "Processing message '%s' from %s (%s)",
            text,
            sender_name,
            sender_phone_number,
            extra=logger_extra,
        )

        await self.whatsapp_api.send_message(to=sender_phone_number, text=response_text)

        await self._broker_service.upsert_from_interaction(
            phone_number=sender_phone_number,
            name=sender_name,
        )
