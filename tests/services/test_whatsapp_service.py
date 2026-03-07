"""Tests for WhatsAppService."""

import os
import unittest
from unittest.mock import AsyncMock, MagicMock

from tests.keys_test import DEFAULT_KEYS

for key, value in DEFAULT_KEYS.items():
    os.environ.setdefault(key, value)

from delpro_backend.services.whatsapp_service import WhatsAppService  # noqa: E402


def _make_service(assistant_service=None, broker_service=None, whatsapp_api=None):
    """Create a WhatsAppService with mocked dependencies."""
    return WhatsAppService(
        assistant_service=assistant_service or AsyncMock(),
        broker_service=broker_service or AsyncMock(),
        whatsapp_api=whatsapp_api or MagicMock(),
    )


class TestHandleMessage(unittest.IsolatedAsyncioTestCase):
    """Tests for handle_message."""

    async def test_processes_valid_message_and_sends_reply(self):
        """Test that a valid message is processed and reply is sent."""
        mock_assistant = AsyncMock()
        mock_assistant.chat = AsyncMock(return_value="Oi! Como posso ajudar?")
        mock_api = AsyncMock()

        svc = _make_service(assistant_service=mock_assistant, whatsapp_api=mock_api)

        await svc.handle_message(
            message_id="msg_123",
            text="Ola",
            sender_phone_number="5511999",
            sender_name="Carlos",
        )

        mock_assistant.chat.assert_awaited_once_with(
            sender_phone_number="5511999",
            user_message="Ola",
            user_name="Carlos",
        )
        mock_api.send_message.assert_awaited_once_with(
            to="5511999", text="Oi! Como posso ajudar?"
        )

    async def test_handle_message_upserts_broker(self):
        """Test that broker upsert is called after processing."""
        mock_broker = AsyncMock()
        mock_api = AsyncMock()
        mock_assistant = AsyncMock()
        mock_assistant.chat = AsyncMock(return_value="resp")

        svc = _make_service(
            assistant_service=mock_assistant,
            broker_service=mock_broker,
            whatsapp_api=mock_api,
        )

        await svc.handle_message(
            message_id="msg_1",
            text="Hi",
            sender_phone_number="5511999",
            sender_name="Tester",
        )

        mock_broker.upsert_from_interaction.assert_awaited_once_with(
            phone_number="5511999", name="Tester"
        )

    async def test_reset_memory_clears_history_and_sends_confirmation(self):
        """Test that /reset memory clears history and sends confirmation without calling chat."""
        mock_assistant = AsyncMock()
        mock_api = AsyncMock()
        svc = _make_service(assistant_service=mock_assistant, whatsapp_api=mock_api)

        await svc.handle_message(
            message_id="msg_1",
            text="/reset memory",
            sender_phone_number="5511999",
            sender_name="User",
        )

        mock_assistant.clear_history.assert_awaited_once_with("5511999")
        mock_api.send_message.assert_awaited_once_with(
            to="5511999", text="Memória resetada."
        )
        mock_assistant.chat.assert_not_awaited()


class TestSignatureRequired(unittest.IsolatedAsyncioTestCase):
    """Tests for signature_required."""

    async def test_raises_403_on_bad_signature(self):
        """Test that invalid signature raises HTTPException 403."""
        import json

        from fastapi import HTTPException

        svc = _make_service()
        body_data = json.dumps({"test": "data"}).encode()

        mock_request = MagicMock()
        mock_request.headers = {"X-Hub-Signature-256": "sha256=invalidsignature"}
        mock_request.body = AsyncMock(return_value=body_data)

        with self.assertRaises(HTTPException) as ctx:
            await svc.signature_required(mock_request)

        self.assertEqual(ctx.exception.status_code, 403)

    async def test_returns_body_on_valid_signature(self):
        """Test that valid signature returns parsed body dict."""
        import hashlib
        import hmac
        import json

        from delpro_backend.utils.settings import settings

        svc = _make_service()

        body_data = {"hello": "world"}
        payload = json.dumps(body_data).encode("utf-8")
        expected_sig = hmac.new(
            bytes(settings.WHATSAPP_APP_SECRET, "latin-1"),
            msg=payload,
            digestmod=hashlib.sha256,
        ).hexdigest()

        mock_request = MagicMock()
        mock_request.headers = {"X-Hub-Signature-256": f"sha256={expected_sig}"}
        mock_request.body = AsyncMock(return_value=payload)

        result = await svc.signature_required(mock_request)

        self.assertEqual(result, body_data)
