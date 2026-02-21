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


async def upload_media(file_bytes: bytes, mime_type: str, filename: str, phone_number: str):
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

    await send_message(to=phone_number, msg_type="image", media_id=media_id)


async def send_message(
    *,
    to: str,
    msg_type: str = "text",
    text: str | None = None,
    media_id: str | None = None,
):
    """Send a WhatsApp message (text or image).

    Args:
        to: Recipient phone number.
        msg_type: ``"text"`` or ``"image"``.
        text: Message body (required when *msg_type* is ``"text"``).
        media_id: Uploaded media ID (required when *msg_type* is ``"image"``).
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

    async with httpx.AsyncClient() as client:
        response = await client.post(
            url, content=json.dumps(payload), headers=headers, timeout=10.0
        )
        response.raise_for_status()
        logger.info("WhatsApp %s message sent to %s", msg_type, to, extra=_logger_extra)
