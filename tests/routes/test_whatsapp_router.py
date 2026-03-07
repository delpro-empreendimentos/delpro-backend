"""Tests for whatsapp_router via TestClient."""

import json
import os
import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from tests.keys_test import DEFAULT_KEYS

for key, value in DEFAULT_KEYS.items():
    os.environ.setdefault(key, value)

from delpro_backend.main import app  # noqa: E402
from delpro_backend.routes.v1.whatsapp_router import whatsapp_service  # noqa: E402


def _valid_wpp_body() -> dict:
    """Return a minimal valid WhatsApp webhook payload."""
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "entry-id",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {"phone_number_id": "test-phone-id"},
                            "contacts": [{"profile": {"name": "Test User"}, "wa_id": "5511999"}],
                            "messages": [
                                {
                                    "from": "5511999",
                                    "id": "msg-id-001",
                                    "timestamp": "1700000000",
                                    "text": {"body": "Hello"},
                                    "type": "text",
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }


class TestWebhookValidation(unittest.TestCase):
    """Tests for GET /webhook verification endpoint."""

    def setUp(self):
        self.client = TestClient(app, raise_server_exceptions=False)

    def test_valid_verification_returns_200(self):
        """Test that valid hub.verify_token returns challenge.

        The router compares hub.verify_token against settings.WHATSAPP_ACCESS_TOKEN.
        In tests this equals 'test-token' (see DEFAULT_KEYS).
        """
        response = self.client.get(
            "/webhook",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "token",
                "hub.challenge": "my-challenge",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"my-challenge")

    def test_invalid_token_returns_422(self):
        """Test that wrong verify_token returns 422."""
        response = self.client.get(
            "/webhook",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "wrong-token",
                "hub.challenge": "my-challenge",
            },
        )
        self.assertEqual(response.status_code, 422)

    def test_missing_params_returns_422(self):
        """Test that missing query params returns 422 (all None ->raises WebhookValidationError)."""
        response = self.client.get("/webhook")
        self.assertEqual(response.status_code, 422)


class TestWebhookReceiveMessage(unittest.TestCase):
    """Tests for POST /webhook message handling endpoint."""

    def setUp(self):
        self.client = TestClient(app, raise_server_exceptions=False)

    def tearDown(self):
        """Clear dependency overrides after each test."""
        app.dependency_overrides.clear()

    @patch("delpro_backend.routes.v1.whatsapp_router.whatsapp_service")
    def test_valid_message_returns_200(self, mock_svc):
        """Test that a valid signed message returns 200."""
        body = _valid_wpp_body()
        mock_svc.handle_message = AsyncMock(return_value=None)

        async def _fake_sig():
            return body

        app.dependency_overrides[whatsapp_service.signature_required] = _fake_sig

        response = self.client.post(
            "/webhook",
            content=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
        )

        self.assertEqual(response.status_code, 200)

    @patch("delpro_backend.routes.v1.whatsapp_router.preprocessing_service")
    def test_preprocessing_service_process_called(self, mock_preprocessing):
        """Test that preprocessing_service.process is called with body and background_tasks."""
        from fastapi import Response
        from starlette import status

        body = _valid_wpp_body()
        mock_preprocessing.process = AsyncMock(
            return_value=Response(status_code=status.HTTP_200_OK)
        )

        async def _fake_sig():
            return body

        app.dependency_overrides[whatsapp_service.signature_required] = _fake_sig

        self.client.post(
            "/webhook",
            content=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
        )

        mock_preprocessing.process.assert_awaited_once()


class TestWebhookDevEndpoint(unittest.TestCase):
    """Tests for POST /webhook/dev endpoint."""

    def setUp(self):
        self.client = TestClient(app, raise_server_exceptions=False)

    def test_dev_endpoint_rejects_bad_token(self):
        """Returns 403 when X-Dev-Token header is wrong."""
        response = self.client.post(
            "/webhook/dev",
            json=_valid_wpp_body(),
            headers={"X-Dev-Token": "wrong-token"},
        )
        self.assertEqual(response.status_code, 403)

    @patch("delpro_backend.routes.v1.whatsapp_router.preprocessing_service")
    def test_dev_endpoint_accepts_valid_token(self, mock_preprocessing):
        """Returns 200 when X-Dev-Token matches DEV_INTERNAL_TOKEN."""
        from fastapi import Response
        from starlette import status as http_status

        from delpro_backend.utils.settings import settings

        mock_preprocessing.process_dev = AsyncMock(
            return_value=Response(status_code=http_status.HTTP_200_OK)
        )

        response = self.client.post(
            "/webhook/dev",
            json=_valid_wpp_body(),
            headers={"X-Dev-Token": settings.DEV_INTERNAL_TOKEN},
        )
        self.assertEqual(response.status_code, 200)
        mock_preprocessing.process_dev.assert_awaited_once()
