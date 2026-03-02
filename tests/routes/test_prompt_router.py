"""Tests for prompt_router via TestClient."""

import datetime
import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from tests.keys_test import DEFAULT_KEYS

for key, value in DEFAULT_KEYS.items():
    os.environ.setdefault(key, value)

from delpro_backend.main import app  # noqa: E402


def _make_prompt_row(content="Default prompt", updated_at=None):
    """Create a MagicMock representing a PromptRow."""
    row = MagicMock()
    row.content = content
    row.updated_at = updated_at or datetime.datetime(2024, 1, 1, tzinfo=datetime.UTC)
    return row


class TestPromptRouterGet(unittest.TestCase):
    """Tests for GET /prompt endpoint."""

    def setUp(self):
        self.client = TestClient(app, raise_server_exceptions=False)

    @patch("delpro_backend.routes.v1.prompt_router.AsyncSessionFactory")
    def test_get_existing_prompt_returns_200(self, mock_factory):
        """Test getting an existing prompt returns 200 with content."""
        mock_row = _make_prompt_row(content="You are a helpful assistant.")
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=mock_row)
        mock_factory.return_value.__aenter__.return_value = mock_session

        response = self.client.get("/prompt")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["content"], "You are a helpful assistant.")
        self.assertIsNotNone(body["updated_at"])

    @patch("delpro_backend.routes.v1.prompt_router.AsyncSessionFactory")
    def test_get_seeds_from_yaml_when_no_row(self, mock_factory):
        """Test that when no row exists, it seeds from prompt.yml and returns 200."""
        mock_row = _make_prompt_row(content="Seeded prompt content")
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=None)
        mock_session.refresh = AsyncMock(side_effect=lambda row: setattr(row, "updated_at", None) or None)
        mock_factory.return_value.__aenter__.return_value = mock_session

        # After add + commit + refresh the row is available via session.add
        # We need to capture the added row
        added_rows = []
        mock_session.add = MagicMock(side_effect=lambda row: added_rows.append(row))

        # Simulate refresh setting updated_at
        async def refresh_side_effect(row):
            row.updated_at = None

        mock_session.refresh = AsyncMock(side_effect=refresh_side_effect)

        response = self.client.get("/prompt")

        self.assertEqual(response.status_code, 200)
        mock_session.add.assert_called_once()
        mock_session.commit.assert_awaited_once()

    @patch("delpro_backend.routes.v1.prompt_router.AsyncSessionFactory")
    def test_get_prompt_no_updated_at(self, mock_factory):
        """Test that prompt with no updated_at returns None for updated_at field."""
        mock_row = _make_prompt_row(content="Test prompt", updated_at=None)
        mock_row.updated_at = None
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=mock_row)
        mock_factory.return_value.__aenter__.return_value = mock_session

        response = self.client.get("/prompt")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIsNone(body["updated_at"])


class TestPromptRouterUpdate(unittest.TestCase):
    """Tests for PUT /prompt endpoint."""

    def setUp(self):
        self.client = TestClient(app, raise_server_exceptions=False)

    @patch("delpro_backend.routes.v1.prompt_router.AsyncSessionFactory")
    def test_update_existing_prompt_returns_200(self, mock_factory):
        """Test updating an existing prompt returns 200 with new content."""
        mock_row = _make_prompt_row(content="Updated prompt")
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=mock_row)
        mock_session.refresh = AsyncMock(return_value=None)
        mock_factory.return_value.__aenter__.return_value = mock_session

        response = self.client.put(
            "/prompt",
            json={"content": "Updated prompt"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["content"], "Updated prompt")

    @patch("delpro_backend.routes.v1.prompt_router.AsyncSessionFactory")
    def test_update_creates_row_when_none_exists(self, mock_factory):
        """Test that updating when no row exists creates a new one."""
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=None)

        new_row = _make_prompt_row(content="New content")
        added_rows = []
        mock_session.add = MagicMock(side_effect=lambda row: added_rows.append(row))

        async def refresh_side_effect(row):
            row.content = "New content"
            row.updated_at = datetime.datetime(2024, 6, 1, tzinfo=datetime.UTC)

        mock_session.refresh = AsyncMock(side_effect=refresh_side_effect)
        mock_factory.return_value.__aenter__.return_value = mock_session

        response = self.client.put(
            "/prompt",
            json={"content": "New content"},
        )

        self.assertEqual(response.status_code, 200)
        mock_session.add.assert_called_once()
        mock_session.commit.assert_awaited_once()


class TestDefaultPrompt(unittest.TestCase):
    """Tests for _default_prompt helper."""

    def test_default_prompt_returns_string(self):
        """Test that _default_prompt returns a non-empty string."""
        from delpro_backend.routes.v1.prompt_router import _default_prompt
        result = _default_prompt()
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)

    def test_default_prompt_fallback_on_exception(self):
        """Test that _default_prompt falls back when load_prompt_config raises."""
        from delpro_backend.routes.v1.prompt_router import _default_prompt
        with patch("delpro_backend.routes.v1.prompt_router.load_prompt_config", side_effect=Exception("fail")):
            result = _default_prompt()
        self.assertEqual(result, "You are a helpful assistant.")
