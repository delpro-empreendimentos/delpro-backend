"""Tests for the database service and models."""

import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

# Ensure DATABASE_URL is available before db_service is imported.
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test_db")

from delpro_backend.db.db_service import DbService
from delpro_backend.db.models import Base, ResourceDocument, ResourceRow


class TestResourceDocument(unittest.TestCase):
    """Tests for the ResourceDocument Pydantic model."""

    def test_create(self):
        """Test creating a ResourceDocument."""
        doc = ResourceDocument(id="abc-123", text="hello")
        self.assertEqual(doc.id, "abc-123")
        self.assertEqual(doc.text, "hello")

    def test_model_dump(self):
        """Test serialising a ResourceDocument to dict."""
        doc = ResourceDocument(id="abc-123", text="hello")
        self.assertEqual(doc.model_dump(), {"id": "abc-123", "text": "hello"})

    def test_model_validate(self):
        """Test deserialising a dict to ResourceDocument."""
        doc = ResourceDocument.model_validate({"id": "abc-123", "text": "hello"})
        self.assertEqual(doc.id, "abc-123")
        self.assertEqual(doc.text, "hello")


class TestResourceRow(unittest.TestCase):
    """Tests for the ResourceRow ORM model."""

    def test_tablename(self):
        """Test that the table name is correct."""
        self.assertEqual(ResourceRow.__tablename__, "resources")

    def test_inherits_base(self):
        """Test that ResourceRow inherits from Base."""
        self.assertTrue(issubclass(ResourceRow, Base))


class TestDbServiceSave(unittest.IsolatedAsyncioTestCase):
    """Tests for DbService.save."""

    @patch("delpro_backend.db.db_service.AsyncSessionFactory")
    async def test_save_inserts_when_not_found(self, mock_factory):
        """Test save creates a new row when resource does not exist."""
        mock_session = AsyncMock()
        mock_session.get.return_value = None
        mock_session.add = MagicMock()
        mock_factory.return_value.__aenter__.return_value = mock_session

        doc = ResourceDocument(id="abc-123", text="hello")
        result = await DbService.save(doc)

        mock_session.add.assert_called_once()
        mock_session.commit.assert_awaited_once()
        self.assertEqual(result.id, "abc-123")
        self.assertEqual(result.text, "hello")

    @patch("delpro_backend.db.db_service.AsyncSessionFactory")
    async def test_save_updates_when_found(self, mock_factory):
        """Test save updates existing row when resource exists."""
        existing = MagicMock(spec=ResourceRow)
        existing.payload = {"id": "abc-123", "text": "old"}

        mock_session = AsyncMock()
        mock_session.get.return_value = existing
        mock_factory.return_value.__aenter__.return_value = mock_session

        doc = ResourceDocument(id="abc-123", text="updated")
        result = await DbService.save(doc)

        mock_session.add.assert_not_called()
        self.assertEqual(existing.payload, doc.model_dump())
        mock_session.commit.assert_awaited_once()
        self.assertEqual(result.id, "abc-123")
        self.assertEqual(result.text, "updated")


class TestDbServiceGet(unittest.IsolatedAsyncioTestCase):
    """Tests for DbService.get."""

    @patch("delpro_backend.db.db_service.AsyncSessionFactory")
    async def test_get_returns_document_when_found(self, mock_factory):
        """Test get returns ResourceDocument when resource exists."""
        existing = MagicMock(spec=ResourceRow)
        existing.payload = {"id": "abc-123", "text": "hello"}

        mock_session = AsyncMock()
        mock_session.get.return_value = existing
        mock_factory.return_value.__aenter__.return_value = mock_session

        result = await DbService.get("abc-123")

        self.assertIsNotNone(result)
        if result:
            self.assertEqual(result.id, "abc-123")
            self.assertEqual(result.text, "hello")

    @patch("delpro_backend.db.db_service.AsyncSessionFactory")
    async def test_get_returns_none_when_not_found(self, mock_factory):
        """Test get returns None when resource does not exist."""
        mock_session = AsyncMock()
        mock_session.get.return_value = None
        mock_factory.return_value.__aenter__.return_value = mock_session

        result = await DbService.get("nonexistent")

        self.assertIsNone(result)
