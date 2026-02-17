"""WhatsApp Service for sending and processing messages."""

import hashlib
import hmac
import json

import httpx
from fastapi import HTTPException, Request

from delpro_backend.assistant.assistant_service import AssistantService
from delpro_backend.utils.logger import get_logger
from delpro_backend.utils.settings import settings

logger_extra = {"component.name": "WhatsappService", "component.version": "v1"}
logger = get_logger(__name__)


class WhatsAppService:
    """Service for WhatsApp message operations."""

    def __init__(self, assistant_service: AssistantService):
        """WhatsApp service class module."""
        self._assistant_service = assistant_service

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

    async def _send_whatsapp_message(self, send_message_to: str, text: str):
        """Send a text message via WhatsApp API.

        Args:
            send_message_to: The phone number to send message.
            text: The message text to send.

        Returns:
            The HTTP response from the WhatsApp API.

        Raises:
            httpx.TimeoutException: If the request times out.
            httpx.RequestError: If the request fails.
        """
        headers = {
            "Content-type": "application/json",
            "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
        }

        url = (
            f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}/"
            f"{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
        )

        data = json.dumps(
            {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": send_message_to,
                "type": "text",
                "text": {"preview_url": False, "body": text},
            }
        )

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, content=data, headers=headers, timeout=10.0)

                response.raise_for_status()

                logger.info("WhatsApp message sent to %s", send_message_to, extra=logger_extra)
        except httpx.TimeoutException as e:
            logger.error("WhatsApp request timed out: %s", e, extra=logger_extra)
            raise e
        except httpx.RequestError as e:
            logger.error("WhatsApp request failed: %s", e, extra=logger_extra)
            raise e

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

        message = body["entry"][0]["changes"][0]["value"]["messages"][0]
        message_id = message["id"]

        contact = body["entry"][0]["changes"][0]["value"]["contacts"][0]
        sender_phone_number = contact.get("wa_id") or contact.get("sender_phone_number")
        sender_name = contact["profile"]["name"]
        text = message["text"]["body"]

        logger.info(
            "Processing message %s from %s (%s)",
            message_id,
            sender_name,
            sender_phone_number,
            extra=logger_extra,
        )

        response_text = await self._assistant_service.chat(
            session_id=sender_phone_number,
            user_message=text,
            user_name=sender_name,
        )

        # to test only
        if sender_phone_number == "123":
            return response_text

        await self._send_whatsapp_message(sender_phone_number, response_text)
