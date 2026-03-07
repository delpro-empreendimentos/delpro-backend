"""Low-level async helpers for the WhatsApp Cloud API.

These are pure functions (no class state) so they can be imported anywhere
without circular-dependency issues.
"""

import json

import httpx

from delpro_backend.utils.logger import get_logger
from delpro_backend.utils.settings import settings

logger = get_logger(__name__)
_logger_extra = {"component.name": "WhatsAppAPI", "component.version": "v1"}


class WhatsappAPI:
    """WhatsApp Cloud API client for sending messages and uploading media.

    This class provides async methods to interact with the WhatsApp Cloud API,
    including uploading media files, sending messages, and managing message status.
    """

    async def upload_media(
        self, file_bytes: bytes, mime_type: str, filename: str, phone_number: str
    ):
        """Upload a media file to WhatsApp and return the media ID.

        Args:
            file_bytes: Raw bytes of the file to upload.
            mime_type: MIME type (e.g. ``image/jpeg``).
            filename: Filename for the multipart upload.
            phone_number: Recipient phone number for sending the media.

        Returns:
            The media ID returned by the WhatsApp API.
        """
        url = (
            f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}/"
            f"{settings.WHATSAPP_PHONE_NUMBER_ID}/media"
        )
        headers = {"Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}"}

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers=headers,
                data={"messaging_product": "whatsapp"},
                files={"file": (filename, file_bytes, mime_type)},
                timeout=30.0,
            )
            response.raise_for_status()
            media_id: str = response.json()["id"]
            logger.info("Uploaded media, id=%s", media_id, extra=_logger_extra)

        if mime_type == "application/pdf":
            await self.send_message(
                to=phone_number,
                msg_type="document",
                media_id=media_id,
                filename=filename,
            )
        else:
            await self.send_message(to=phone_number, msg_type="image", media_id=media_id)

    async def set_typing_status(self, whatsapp_message_id: str):
        """Mark a WhatsApp message as read and show typing indicator.

        Args:
            whatsapp_message_id: The WhatsApp message ID to mark as read.
        """
        url = (
            f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}/"
            f"{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
        )
        headers = {
            "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
            "Content-Type": "application/json",
        }

        body = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": whatsapp_message_id,
            "typing_indicator": {"type": "text"},
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers=headers,
                content=json.dumps(body),
                timeout=30.0,
            )
            response.raise_for_status()

            logger.info(
                "Typing status set to message: %s", whatsapp_message_id, extra=_logger_extra
            )

    async def send_form_to_user(self, send_phone_number: str):
        """Mark a WhatsApp message as read and show typing indicator.

        Args:
            send_phone_number: The phone number to send the form to.
        """
        url = (
            f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}/"
            f"{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
        )
        headers = {
            "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
            "Content-Type": "application/json",
        }

        body = {
            "messaging_product": "whatsapp",
            "to": send_phone_number,
            "type": "template",
            "template": {
                "name": "informacoes_corretor",
                "language": {"code": "pt_BR"},
                "components": [
                    {
                        "type": "button",
                        "sub_type": "flow",
                        "index": "0",
                        "parameters": [
                            {"type": "action", "action": {"flow_token": "informacoes_corretor"}}
                        ],
                    }
                ],
            },
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers=headers,
                content=json.dumps(body),
                timeout=30.0,
            )
            response.raise_for_status()

            # logger.info(
            #     "Typing status set to message: %s", whatsapp_message_id, extra=_logger_extra
            # )

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

    def is_valid_whatsapp_message(self, body: dict) -> bool:
        """Check if the incoming webhook event has a valid WhatsApp message structure."""
        try:
            message = body["entry"][0]["changes"][0]["value"]["messages"][0]
            return bool(body.get("object") and message)
        except (KeyError, IndexError, TypeError):
            return False

    async def send_message(
        self,
        *,
        to: str,
        msg_type: str = "text",
        text: str | None = None,
        media_id: str | None = None,
        filename: str | None = None,
    ):
        """Send a WhatsApp message (text, image, or document).

        Args:
            to: Recipient phone number.
            msg_type: ``"text"``, ``"image"``, or ``"document"``.
            text: Message body (required when *msg_type* is ``"text"``).
            media_id: Uploaded media ID (required when *msg_type* is ``"image"`` or ``"document"``).
            filename: Filename for document messages.
        """
        url = (
            f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}/"
            f"{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
        )
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
        }

        payload: dict = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": msg_type,
        }

        if msg_type == "text":
            payload["text"] = {"preview_url": False, "body": text}
        elif msg_type == "image":
            payload["image"] = {"id": media_id}
        elif msg_type == "document":
            payload["document"] = {"id": media_id, "filename": filename}

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url, content=json.dumps(payload), headers=headers, timeout=10.0
            )
            response.raise_for_status()
            logger.info("WhatsApp %s message sent to %s", msg_type, to, extra=_logger_extra)
