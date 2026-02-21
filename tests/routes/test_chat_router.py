"""Tests for the /test router endpoint (WhatsApp message simulation)."""

import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from tests.keys_test import DEFAULT_KEYS

for key, value in DEFAULT_KEYS.items():
    os.environ.setdefault(key, value)

from delpro_backend.main import app  # noqa: E402


def _valid_body(phone="5511999990000", name="Carlos", text="Ola"):
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "contacts": [{"wa_id": phone, "profile": {"name": name}}],
                            "messages": [{"id": "msg-1", "text": {"body": text}}],
                        }
                    }
                ]
            }
        ],
    }


class TestTestRouterPost(unittest.TestCase):
    """Tests for POST /test endpoint."""

    def setUp(self):
        self.client = TestClient(app, raise_server_exceptions=False)

    @patch("delpro_backend.routes.v1.evaluate_router.whatsapp_service")
    def test_success_returns_200(self, mock_wpp_svc):
        """Test successful POST /test returns 200."""
        mock_wpp_svc.handle_message = AsyncMock(return_value="Olá!")

        response = self.client.post("/test", json=_valid_body())

        self.assertEqual(response.status_code, 200)

    @patch("delpro_backend.routes.v1.evaluate_router.whatsapp_service")
    def test_non_message_body_returns_200(self, mock_wpp_svc):
        """Test status-update payload returns 200 (handle_message returns None)."""
        mock_wpp_svc.handle_message = AsyncMock(return_value=None)

        body = {"entry": [{"changes": [{"value": {"statuses": [{"id": "x"}]}}]}]}
        response = self.client.post("/test", json=body)

        self.assertEqual(response.status_code, 200)

    @patch("delpro_backend.routes.v1.evaluate_router.whatsapp_service")
    def test_internal_error_returns_500(self, mock_wpp_svc):
        """Test that unhandled exceptions return 500."""
        mock_wpp_svc.handle_message = AsyncMock(side_effect=RuntimeError("boom"))

        response = self.client.post("/test", json=_valid_body())

        self.assertEqual(response.status_code, 500)
