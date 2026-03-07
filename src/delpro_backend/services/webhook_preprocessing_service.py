"""Pre-processing logic for incoming WhatsApp webhook payloads."""

import json

import httpx
from fastapi import BackgroundTasks
from fastapi.responses import Response
from starlette import status

from delpro_backend.services.whatsapp_api import WhatsappAPI
from delpro_backend.services.whatsapp_service import WhatsAppService
from delpro_backend.utils import dev_state
from delpro_backend.utils.logger import get_logger
from delpro_backend.utils.settings import settings

logger_extra = {"component.name": "WebhookPreProcessingService", "component.version": "v1"}
logger = get_logger(__name__)


class WebhookPreProcessingService:
    """Handles pre-processing of webhook payloads before dispatching background tasks."""

    def __init__(self, whatsapp_api: WhatsappAPI, whatsapp_service: WhatsAppService) -> None:
        """Initialize the WebhookPreProcessingService with WhatsApp API and service instances."""
        self._whatsapp_api = whatsapp_api
        self._whatsapp_service = whatsapp_service

    async def process(self, body: dict, background_tasks: BackgroundTasks) -> Response:
        """Process a verified webhook payload from WhatsApp Cloud API."""
        logger.info("Received this payload: %s", json.dumps(body), extra=logger_extra)

        message_id, text, sender_phone_number, sender_name = (
            self._whatsapp_api.extract_information_whatsapp_message(body=body)
        )

        if not message_id:
            logger.debug(
                "Skipping non-message webhook (status update or unsupported type)",
                extra=logger_extra,
            )
            return Response(status_code=status.HTTP_200_OK)

        logger.info(
            "Was a valid message!: %s, %s, %s, %s",
            message_id,
            text,
            sender_phone_number,
            sender_name,
            extra=logger_extra,
        )

        # TODO: validate what is true message and what is not

        if sender_phone_number == settings.DEV_PHONE:
            return await self._handle_dev_message(
                body=body,
                text=text,
                sender_phone_number=sender_phone_number,
                sender_name=sender_name,
                background_tasks=background_tasks,
            )

        # await self._whatsapp_api.set_typing_status(message_id)

        background_tasks.add_task(
            self._whatsapp_service.handle_message,
            sender_name=sender_name,
            sender_phone_number=sender_phone_number,
            text=text,
        )
        return Response(status_code=status.HTTP_200_OK)

    async def _handle_dev_message(
        self,
        body: dict,
        text: str,
        sender_name: str,
        sender_phone_number: str,
        background_tasks: BackgroundTasks,
    ) -> Response:
        if text == "/dev":
            active = dev_state.toggle()

            status_msg = (
                f"Dev mode ON -> {settings.DEV_TUNNEL_URL}" if active else "Dev mode OFF -> cloud"
            )

            await self._whatsapp_api.send_message(to=sender_phone_number, text=status_msg)

            return Response(status_code=status.HTTP_200_OK)

        if dev_state.is_active() and settings.DEV_TUNNEL_URL:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{settings.DEV_TUNNEL_URL}/webhook/dev",
                    json=body,
                    headers={"X-Dev-Token": settings.DEV_INTERNAL_TOKEN},
                    timeout=30,
                )
                return Response(status_code=status.HTTP_200_OK)

        background_tasks.add_task(
            self._whatsapp_service.handle_message,
            sender_name=sender_name,
            sender_phone_number=sender_phone_number,
            text=text,
        )

        return Response(status_code=status.HTTP_200_OK)

    async def process_dev(self, body: dict, background_tasks: BackgroundTasks) -> Response:
        """Process a forwarded payload received on the local dev tunnel endpoint."""
        message_id, text, sender_phone_number, sender_name = (
            self._whatsapp_api.extract_information_whatsapp_message(body=body)
        )

        # await self._whatsapp_api.set_typing_status(message_id)

        background_tasks.add_task(
            self._whatsapp_service.handle_message,
            sender_name=sender_name,
            sender_phone_number=sender_phone_number,
            text=text,
        )

        return Response(status_code=status.HTTP_200_OK)
