"""Tests for WhatsAppService."""

import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from tests.keys_test import DEFAULT_KEYS

for key, value in DEFAULT_KEYS.items():
    os.environ.setdefault(key, value)

from delpro_backend.services.whatsapp_service import WhatsAppService  # noqa: E402


def _make_service(assistant_service=None, broker_service=None):
    """Create a WhatsAppService with mocked dependencies."""
    return WhatsAppService(
        assistant_service=assistant_service or AsyncMock(),
        broker_service=broker_service or AsyncMock(),
    )


def _make_message_body(message_id="msg_123", phone="5511999999999", name="John", text="Hi"):
    """Create a valid WhatsApp webhook payload."""
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "contacts": [{"wa_id": phone, "profile": {"name": name}}],
                            "messages": [{"id": message_id, "text": {"body": text}}],
                        }
                    }
                ]
            }
        ],
    }


class TestIsValidWhatsappMessage(unittest.TestCase):
    """Tests for is_valid_whatsapp_message."""

    def test_valid_message_returns_true(self):
        """Test that a valid message body returns True."""
        svc = _make_service()
        body = _make_message_body()
        self.assertTrue(svc.is_valid_whatsapp_message(body))

    def test_missing_object_returns_false(self):
        """Test that a body without 'object' returns False."""
        svc = _make_service()
        body = _make_message_body()
        body.pop("object")
        self.assertFalse(svc.is_valid_whatsapp_message(body))

    def test_missing_messages_returns_false(self):
        """Test that a body without messages returns False."""
        svc = _make_service()
        body = {
            "object": "whatsapp_business_account",
            "entry": [{"changes": [{"value": {"contacts": []}}]}],
        }
        self.assertFalse(svc.is_valid_whatsapp_message(body))

    def test_empty_body_returns_false(self):
        """Test that an empty body returns False."""
        svc = _make_service()
        self.assertFalse(svc.is_valid_whatsapp_message({}))


class TestExtractInformationWhatsappMessage(unittest.TestCase):
    """Tests for extract_information_whatsapp_message."""

    def test_extracts_wa_id(self):
        """Test extraction uses wa_id when present."""
        svc = _make_service()
        body = _make_message_body(phone="5511111111111", name="Alice", text="Hello")
        msg_id, text, phone, name = svc.extract_information_whatsapp_message(body)
        self.assertEqual(phone, "5511111111111")
        self.assertEqual(name, "Alice")
        self.assertEqual(text, "Hello")

    def test_extracts_sender_phone_fallback(self):
        """Test extraction falls back to sender_phone_number when wa_id is absent."""
        svc = _make_service()
        body = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "contacts": [
                                    {"sender_phone_number": "5522222222222", "profile": {"name": "Bob"}}
                                ],
                                "messages": [{"id": "m1", "text": {"body": "Hi"}}],
                            }
                        }
                    ]
                }
            ],
        }
        msg_id, text, phone, name = svc.extract_information_whatsapp_message(body)
        self.assertEqual(phone, "5522222222222")
        self.assertEqual(name, "Bob")

    def test_extract_returns_empty_strings_on_malformed_body(self):
        """Test that extract_information returns empty strings for malformed body."""
        svc = _make_service()
        result = svc.extract_information_whatsapp_message({"bad": "data"})
        self.assertEqual(result, ("", "", "", ""))


class TestHandleMessage(unittest.IsolatedAsyncioTestCase):
    """Tests for handle_message."""

    async def test_returns_none_for_invalid_message(self):
        """Test that None is returned for non-message webhooks."""
        svc = _make_service()
        body = {"entry": [{"changes": [{"value": {"statuses": [{"id": "x"}]}}]}]}
        result = await svc.handle_message(body)
        self.assertIsNone(result)

    async def test_returns_empty_string_when_phone_number_empty(self):
        """Test that empty string is returned when phone extraction fails."""
        svc = _make_service()

        with patch.object(
            svc, "is_valid_whatsapp_message", return_value=True
        ), patch.object(
            svc, "extract_information_whatsapp_message", return_value=("", "", "", "")
        ):
            result = await svc.handle_message({})

        self.assertEqual(result, "")

    async def test_processes_valid_message_and_sends_reply(self):
        """Test that a valid message is processed and reply is sent."""
        mock_assistant = AsyncMock()
        mock_assistant.chat = AsyncMock(return_value="Oi! Como posso ajudar?")

        svc = _make_service(assistant_service=mock_assistant)

        with (
            patch.object(
                svc, "extract_information_whatsapp_message",
                return_value=("msg_123", "Ola", "5511999", "Carlos"),
            ),
            patch("delpro_backend.services.whatsapp_service.whatsapp_api") as mock_api,
        ):
            mock_api.set_typing_status = AsyncMock()
            mock_api.send_message = AsyncMock()

            body = _make_message_body(phone="5511999", name="Carlos", text="Ola")
            await svc.handle_message(body)

            mock_assistant.chat.assert_awaited_once_with(
                sender_phone_number="5511999",
                user_message="Ola",
                user_name="Carlos",
            )
            mock_api.send_message.assert_awaited_once_with(
                to="5511999", text="Oi! Como posso ajudar?"
            )

    async def test_handle_message_processes_valid_phone_number(self):
        """Test that a message with a valid phone number is fully processed."""
        mock_assistant = AsyncMock()
        mock_assistant.chat = AsyncMock(return_value="Test response")

        mock_broker_svc = AsyncMock()
        mock_broker_svc.upsert_from_interaction = AsyncMock()

        svc = _make_service(assistant_service=mock_assistant, broker_service=mock_broker_svc)

        with patch("delpro_backend.services.whatsapp_service.whatsapp_api") as mock_api:
            mock_api.set_typing_status = AsyncMock()
            mock_api.send_message = AsyncMock()

            body = _make_message_body(phone="5511999", name="Tester", text="Test")
            await svc.handle_message(body)

            mock_assistant.chat.assert_awaited_once()
            mock_api.send_message.assert_awaited_once_with(to="5511999", text="Test response")


class TestSignatureRequired(unittest.IsolatedAsyncioTestCase):
    """Tests for signature_required."""

    async def test_raises_403_on_bad_signature(self):
        """Test that invalid signature raises HTTPException 403."""
        import hashlib
        import hmac
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
