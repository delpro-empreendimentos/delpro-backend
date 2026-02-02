"""Tests for the chat router endpoints."""

import os
import unittest
from unittest.mock import AsyncMock, patch

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test_db")
os.environ.setdefault("WPP_PHONE_ID", "test")
os.environ.setdefault("WPP_TEST_NUMER", "test")
os.environ.setdefault("WPP_TOKEN", "test")
os.environ.setdefault("API_KEY", "test")
os.environ.setdefault("PROJECT_ID", "test")
os.environ.setdefault("GEMINI_MODEL", "gemini-2.0-flash")
os.environ.setdefault("MAX_TOKENS", "1024")
os.environ.setdefault("LLM_TEMPERATURE", "0")
os.environ.setdefault("MAX_HISTORY_MESSAGES", "20")

from fastapi.testclient import TestClient

from delpro_backend.main import app


class TestSendMessage(unittest.TestCase):
    """Tests for the POST /chat endpoint."""

    def setUp(self):
        """Set up the test client."""
        self.client = TestClient(app, raise_server_exceptions=False)

    @patch("delpro_backend.routes.v1.chat_router.AssistantService.chat", new_callable=AsyncMock)
    def test_success(self, mock_chat):
        """Test successful message returns 200 with structured response."""
        mock_chat.return_value = "Hello! How can I help you today?"

        response = self.client.post(
            "/chat",
            json={"session_id": "5511999990000", "input": "Ola!", "user_name": "Carlos Mendes"},
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["session_id"], "5511999990000")
        self.assertEqual(data["response"], "Hello! How can I help you today?")

        # Verify that chat was called with user_name
        mock_chat.assert_called_once_with(
            session_id="5511999990000",
            user_message="Ola!",
            user_name="Carlos Mendes",
        )

    def test_missing_session_id(self):
        """Test missing session_id returns 422."""
        response = self.client.post(
            "/chat",
            json={"input": "hello", "user_name": "John Doe"},
        )
        self.assertEqual(response.status_code, 422)

    def test_missing_input(self):
        """Test missing input returns 422."""
        response = self.client.post(
            "/chat",
            json={"session_id": "test-session", "user_name": "John Doe"},
        )
        self.assertEqual(response.status_code, 422)

    def test_missing_user_name(self):
        """Test missing user_name returns 422."""
        response = self.client.post(
            "/chat",
            json={"session_id": "test-session", "input": "hello"},
        )
        self.assertEqual(response.status_code, 422)

    def test_empty_session_id(self):
        """Test empty session_id returns 422."""
        response = self.client.post(
            "/chat",
            json={"session_id": "", "input": "hello", "user_name": "John Doe"},
        )
        self.assertEqual(response.status_code, 422)

    def test_empty_input(self):
        """Test empty input returns 422."""
        response = self.client.post(
            "/chat",
            json={"session_id": "test-session", "input": "", "user_name": "John Doe"},
        )
        self.assertEqual(response.status_code, 422)

    @patch("delpro_backend.routes.v1.chat_router.AssistantService.chat", new_callable=AsyncMock)
    def test_internal_error(self, mock_chat):
        """Test that exceptions are handled and return 500."""
        mock_chat.side_effect = Exception("LLM unavailable")

        response = self.client.post(
            "/chat",
            json={"session_id": "test-session", "input": "hello", "user_name": "John Doe"},
        )

        self.assertEqual(response.status_code, 500)
