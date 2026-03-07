"""Tests for WebhookPreProcessingService."""

import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from tests.keys_test import DEFAULT_KEYS

for key, value in DEFAULT_KEYS.items():
    os.environ.setdefault(key, value)

from delpro_backend.services.webhook_preprocessing_service import (
    WebhookPreProcessingService,  # noqa: E402
)


def _valid_body():
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "contacts": [{"wa_id": "5511999", "profile": {"name": "Alice"}}],
                            "messages": [{"id": "msg1", "text": {"body": "Ola"}}],
                        }
                    }
                ]
            }
        ],
    }


def _make_service(whatsapp_api=None, whatsapp_service=None):
    return WebhookPreProcessingService(
        whatsapp_api=whatsapp_api or MagicMock(),
        whatsapp_service=whatsapp_service or MagicMock(),
    )


class TestProcess(unittest.IsolatedAsyncioTestCase):
    """Tests for WebhookPreProcessingService.process()."""

    async def test_normal_user_dispatches_background_task(self):
        """Non-DEV_PHONE messages are dispatched as background tasks."""
        mock_api = MagicMock()
        mock_api.extract_information_whatsapp_message.return_value = (
            "msg1",
            "Ola",
            "5511999",
            "Alice",
        )
        mock_api.set_typing_status = AsyncMock()
        mock_svc = MagicMock()
        svc = _make_service(whatsapp_api=mock_api, whatsapp_service=mock_svc)

        mock_bg = MagicMock()

        with patch(
            "delpro_backend.services.webhook_preprocessing_service.settings"
        ) as mock_settings:
            mock_settings.DEV_PHONE = "9999999999"
            response = await svc.process(_valid_body(), mock_bg)

        self.assertEqual(response.status_code, 200)
        mock_bg.add_task.assert_called_once()

    async def test_dev_phone_toggle_activates_dev_mode(self):
        """DEV_PHONE + /dev activates dev mode and sends status message."""
        mock_api = MagicMock()
        mock_api.extract_information_whatsapp_message.return_value = (
            "msg1",
            "/dev",
            "5511111",
            "Dev",
        )
        mock_api.send_message = AsyncMock()
        svc = _make_service(whatsapp_api=mock_api)

        mock_bg = MagicMock()

        with (
            patch(
                "delpro_backend.services.webhook_preprocessing_service.settings"
            ) as mock_settings,
            patch("delpro_backend.services.webhook_preprocessing_service.dev_state") as mock_dev,
        ):
            mock_settings.DEV_PHONE = "5511111"
            mock_settings.DEV_TUNNEL_URL = "https://tunnel.example.com"
            mock_dev.toggle.return_value = True
            mock_dev.is_active.return_value = False

            response = await svc.process(_valid_body(), mock_bg)

        self.assertEqual(response.status_code, 200)
        mock_dev.toggle.assert_called_once()
        mock_api.send_message.assert_awaited_once()

    async def test_dev_phone_toggle_deactivates_dev_mode(self):
        """DEV_PHONE + /dev deactivates dev mode and sends OFF message."""
        mock_api = MagicMock()
        mock_api.extract_information_whatsapp_message.return_value = (
            "msg1",
            "/dev",
            "5511111",
            "Dev",
        )
        mock_api.send_message = AsyncMock()
        svc = _make_service(whatsapp_api=mock_api)

        mock_bg = MagicMock()

        with (
            patch(
                "delpro_backend.services.webhook_preprocessing_service.settings"
            ) as mock_settings,
            patch("delpro_backend.services.webhook_preprocessing_service.dev_state") as mock_dev,
        ):
            mock_settings.DEV_PHONE = "5511111"
            mock_settings.DEV_TUNNEL_URL = None
            mock_dev.toggle.return_value = False
            mock_dev.is_active.return_value = False

            response = await svc.process(_valid_body(), mock_bg)

        self.assertEqual(response.status_code, 200)
        msg_text = mock_api.send_message.call_args.kwargs["text"]
        self.assertIn("OFF", msg_text)

    async def test_dev_phone_forwards_when_active(self):
        """DEV_PHONE with active dev mode forwards request to tunnel URL."""
        mock_api = MagicMock()
        mock_api.extract_information_whatsapp_message.return_value = (
            "msg1",
            "Hello",
            "5511111",
            "Dev",
        )
        svc = _make_service(whatsapp_api=mock_api)

        mock_bg = MagicMock()

        with (
            patch(
                "delpro_backend.services.webhook_preprocessing_service.settings"
            ) as mock_settings,
            patch("delpro_backend.services.webhook_preprocessing_service.dev_state") as mock_dev,
            patch(
                "delpro_backend.services.webhook_preprocessing_service.httpx.AsyncClient"
            ) as mock_client_cls,
        ):
            mock_settings.DEV_PHONE = "5511111"
            mock_settings.DEV_TUNNEL_URL = "https://tunnel.example.com"
            mock_settings.DEV_INTERNAL_TOKEN = "secret"
            mock_dev.is_active.return_value = True

            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            response = await svc.process(_valid_body(), mock_bg)

        self.assertEqual(response.status_code, 200)
        mock_client.post.assert_awaited_once()

    async def test_dev_phone_no_forward_when_inactive(self):
        """DEV_PHONE with inactive dev mode does NOT forward."""
        mock_api = MagicMock()
        mock_api.extract_information_whatsapp_message.return_value = (
            "msg1",
            "Hello",
            "5511111",
            "Dev",
        )
        svc = _make_service(whatsapp_api=mock_api)

        mock_bg = MagicMock()

        with (
            patch(
                "delpro_backend.services.webhook_preprocessing_service.settings"
            ) as mock_settings,
            patch("delpro_backend.services.webhook_preprocessing_service.dev_state") as mock_dev,
            patch(
                "delpro_backend.services.webhook_preprocessing_service.httpx.AsyncClient"
            ) as mock_client_cls,
        ):
            mock_settings.DEV_PHONE = "5511111"
            mock_settings.DEV_TUNNEL_URL = "https://tunnel.example.com"
            mock_dev.is_active.return_value = False

            response = await svc.process(_valid_body(), mock_bg)

        self.assertEqual(response.status_code, 200)
        mock_client_cls.assert_not_called()


class TestProcessDev(unittest.IsolatedAsyncioTestCase):
    """Tests for WebhookPreProcessingService.process_dev()."""

    async def test_process_dev_dispatches_background_task(self):
        """process_dev dispatches handle_message as a background task and returns 200."""
        mock_api = MagicMock()
        mock_api.extract_information_whatsapp_message.return_value = (
            "msg1",
            "Hi",
            "5511999",
            "Bob",
        )
        mock_api.set_typing_status = AsyncMock()
        mock_svc = MagicMock()
        svc = _make_service(whatsapp_api=mock_api, whatsapp_service=mock_svc)

        mock_bg = MagicMock()
        response = await svc.process_dev(_valid_body(), mock_bg)

        self.assertEqual(response.status_code, 200)
        mock_bg.add_task.assert_called_once_with(
            mock_svc.handle_message,
            sender_name="Bob",
            sender_phone_number="5511999",
            text="Hi",
        )
