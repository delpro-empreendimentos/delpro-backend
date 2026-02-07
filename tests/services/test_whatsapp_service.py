"""Tests for WhatsAppService."""

import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

os.environ.update(
    {
        "DATABASE_URL": "postgresql+asyncpg://test:test@localhost:5432/test_db",
        "API_KEY": "test",
        "PROJECT_ID": "test",
        "GEMINI_MODEL": "gemini-2.0-flash",
        "MAX_TOKENS": "1024",
        "LLM_TEMPERATURE": "0",
        "MAX_HISTORY_MESSAGES": "20",
        "LOG_LEVEL": "INFO",
        "MAX_TOKENS_SUMMARY": "1",
        "WHATSAPP_ACCESS_TOKEN": "test-token",
        "WHATSAPP_PHONE_NUMBER_ID": "test-phone-id",
        "WHATSAPP_VERIFY_TOKEN": "test-verify-token",
        "WHATSAPP_APP_SECRET": "test-app-secret",
        "WHATSAPP_API_VERSION": "v21.0",
        "WHATSAPP_RECIPIENT_WAID": "test-recipient",
    }
)

from delpro_backend.services.whatsapp_service import WhatsAppService


def _make_service(redis_client=None, assistant_service=None):
    """Create a WhatsAppService with mocked dependencies."""
    return WhatsAppService(
        assistant_service=assistant_service or AsyncMock(),
        redis_client=redis_client or AsyncMock(),
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


class TestIsMessageProcessed(unittest.IsolatedAsyncioTestCase):
    """Tests for the _is_message_processed method."""

    async def test_returns_false_for_new_message(self):
        """Should return False when Redis SET NX succeeds (new message)."""
        mock_redis = AsyncMock()
        mock_redis.set.return_value = True  # NX succeeded = new key

        service = _make_service(redis_client=mock_redis)
        result = await service._is_message_processed("msg_123")

        self.assertFalse(result)
        mock_redis.set.assert_awaited_once_with("wpp:msg:msg_123", "1", nx=True, ex=300)

    async def test_returns_true_for_duplicate_message(self):
        """Should return True when Redis SET NX fails (key already exists)."""
        mock_redis = AsyncMock()
        mock_redis.set.return_value = None  # NX failed = key exists

        service = _make_service(redis_client=mock_redis)
        result = await service._is_message_processed("msg_123")

        self.assertTrue(result)

    async def test_uses_correct_ttl(self):
        """Should use the configured TTL for message expiry."""
        mock_redis = AsyncMock()
        mock_redis.set.return_value = True

        service = _make_service(redis_client=mock_redis)
        await service._is_message_processed("msg_456")

        mock_redis.set.assert_awaited_once_with(
            "wpp:msg:msg_456", "1", nx=True, ex=WhatsAppService._MESSAGE_TTL_SECONDS
        )


class TestSendMessage(unittest.IsolatedAsyncioTestCase):
    """Tests for the _send_whatsapp_message method."""

    @patch("delpro_backend.services.whatsapp_service.httpx.AsyncClient")
    async def test_sends_message_successfully(self, mock_client_class):
        """Should send message via WhatsApp API."""
        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client

        service = _make_service()
        await service._send_whatsapp_message("5511999999999", "Hello")

        mock_client.post.assert_called_once()

    @patch("delpro_backend.services.whatsapp_service.httpx.AsyncClient")
    async def test_raises_on_timeout(self, mock_client_class):
        """Should raise exception on timeout."""
        import httpx

        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.TimeoutException("Timeout")
        mock_client_class.return_value.__aenter__.return_value = mock_client

        service = _make_service()
        with self.assertRaises(httpx.TimeoutException):
            await service._send_whatsapp_message("5511999999999", "Hello")

    @patch("delpro_backend.services.whatsapp_service.httpx.AsyncClient")
    async def test_raises_on_request_error(self, mock_client_class):
        """Should raise exception on request error."""
        import httpx

        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.RequestError("Connection failed")
        mock_client_class.return_value.__aenter__.return_value = mock_client

        service = _make_service()
        with self.assertRaises(httpx.RequestError):
            await service._send_whatsapp_message("5511999999999", "Hello")


class TestHandleMessage(unittest.IsolatedAsyncioTestCase):
    """Tests for the handle_message method."""

    async def test_processes_new_message_with_wa_id(self):
        """Should process a new message using wa_id and send response."""
        mock_redis = AsyncMock()
        mock_redis.set.return_value = True  # New message

        mock_assistant = AsyncMock()
        mock_assistant.chat.return_value = "Hello there!"

        service = _make_service(redis_client=mock_redis, assistant_service=mock_assistant)

        with patch.object(service, "_send_whatsapp_message", new_callable=AsyncMock) as mock_send:
            body = _make_message_body()
            result = await service.handle_message(body)

            mock_assistant.chat.assert_called_once_with(
                session_id="5511999999999",
                user_message="Hi",
                user_name="John",
            )
            mock_send.assert_awaited_once_with("5511999999999", "Hello there!")
            self.assertEqual(result, "Hello there!")

    async def test_processes_new_message_with_sender_phone_number(self):
        """Should fallback to sender_phone_number if wa_id is not present."""
        mock_redis = AsyncMock()
        mock_redis.set.return_value = True

        mock_assistant = AsyncMock()
        mock_assistant.chat.return_value = "Hello there!"

        service = _make_service(redis_client=mock_redis, assistant_service=mock_assistant)

        body = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "contacts": [
                                    {"sender_phone_number": "5511888888888", "profile": {"name": "Jane"}}
                                ],
                                "messages": [{"id": "msg_456", "text": {"body": "Hello"}}],
                            }
                        }
                    ]
                }
            ],
        }

        with patch.object(service, "_send_whatsapp_message", new_callable=AsyncMock):
            await service.handle_message(body)

            mock_assistant.chat.assert_called_once_with(
                session_id="5511888888888",
                user_message="Hello",
                user_name="Jane",
            )

    async def test_skips_duplicate_message(self):
        """Should skip processing if message was already processed."""
        mock_redis = AsyncMock()
        mock_redis.set.return_value = None  # Duplicate

        mock_assistant = AsyncMock()
        service = _make_service(redis_client=mock_redis, assistant_service=mock_assistant)

        body = _make_message_body()
        result = await service.handle_message(body)

        self.assertIsNone(result)
        mock_assistant.chat.assert_not_called()

    async def test_returns_none_for_status_update(self):
        """Should return None for status update payloads."""
        service = _make_service()

        body = {
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "statuses": [{"id": "msg_123", "status": "delivered"}],
                            }
                        }
                    ]
                }
            ]
        }

        result = await service.handle_message(body)
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
