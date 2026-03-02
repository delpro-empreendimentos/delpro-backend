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


whatsapp_api = WhatsappAPI()


class WhatsAppService:
    """Service for WhatsApp message operations."""

    def __init__(self, assistant_service: AssistantService, broker_service: BrokerService):
        """WhatsApp service class module."""
        self._assistant_service = assistant_service
        self._broker_service = broker_service

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

    def is_valid_whatsapp_message(self, body: dict) -> bool:
        """Check if the incoming webhook event has a valid WhatsApp message structure."""
        try:
            message = body["entry"][0]["changes"][0]["value"]["messages"][0]
            return bool(body.get("object") and message)
        except (KeyError, IndexError, TypeError):
            return False

    def extract_information_whatsapp_message(self, body: dict) -> tuple[str, str, str, str]:
        """Extract message information from a WhatsApp webhook payload.

        Args:
            body: The webhook payload from WhatsApp.

        Returns:
            A tuple of (message_id, text, sender_phone_number, sender_name).
        """
        try:
            message = body["entry"][0]["changes"][0]["value"]["messages"][0]
            message_id = message["id"]

            contact = body["entry"][0]["changes"][0]["value"]["contacts"][0]
            sender_phone_number = contact.get("wa_id") or contact.get("sender_phone_number")
            sender_name = contact["profile"]["name"]
            text = message["text"]["body"]
            return message_id, text, sender_phone_number, sender_name
        except Exception:
            return "", "", "", ""

    async def handle_message(self, body: dict):
        """Process an incoming WhatsApp message and send a response.

        Args:
            body: The webhook payload from WhatsApp.

        Returns:
            None for status updates/duplicates (acknowledged but not processed),
            or response dict for processed messages.
        """
        if not self.is_valid_whatsapp_message(body):
            logger.info("Non-message webhook event, acknowledging", extra=logger_extra)
            return None

        message_id, text, sender_phone_number, sender_name = (
            self.extract_information_whatsapp_message(body=body)
        )

        # test only
        if sender_phone_number == "":
            return ""

        logger.info(
            "Processing message %s from %s (%s)",
            message_id,
            sender_name,
            sender_phone_number,
            extra=logger_extra,
        )

        response_text = await self._assistant_service.chat(
            sender_phone_number=sender_phone_number,
            user_message=text,
            user_name=sender_name,
        )

        await whatsapp_api.set_typing_status(message_id)
        await self._broker_service.upsert_from_interaction(
            phone_number=sender_phone_number,
            name=sender_name,
        )

        await whatsapp_api.send_message(to=sender_phone_number, text=response_text)
