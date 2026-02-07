"""Tests for the database service and models."""

import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from delpro_backend.db.db_service import DbService
from delpro_backend.models.v1.database_models import Base, MessageRow, ResourceDocument, ResourceRow
from tests.keys_test import DEFAULT_KEYS

for key, value in DEFAULT_KEYS.items():
    os.environ.setdefault(key, value)


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


class TestRowToMessage(unittest.TestCase):
    """Tests for _row_to_message helper function."""

    def test_converts_human_message(self):
        """Test converting MessageRow with role='human' to HumanMessage."""
        row = MagicMock(spec=MessageRow)
        row.role = "human"
        row.content = "Hello"

        result = _row_to_message(row)

        self.assertIsInstance(result, HumanMessage)
        self.assertEqual(result.content, "Hello")

    def test_converts_ai_message(self):
        """Test converting MessageRow with role='ai' to AIMessage."""
        row = MagicMock(spec=MessageRow)
        row.role = "ai"
        row.content = "Hi there!"

        result = _row_to_message(row)

        self.assertIsInstance(result, AIMessage)
        self.assertEqual(result.content, "Hi there!")

    def test_converts_system_message(self):
        """Test converting MessageRow with role='system' to SystemMessage."""
        row = MagicMock(spec=MessageRow)
        row.role = "system"
        row.content = "System message"

        result = _row_to_message(row)

        self.assertIsInstance(result, SystemMessage)
        self.assertEqual(result.content, "System message")

    def test_unknown_role_defaults_to_human(self):
        """Test unknown role defaults to HumanMessage."""
        row = MagicMock(spec=MessageRow)
        row.role = "unknown"
        row.content = "Mystery content"

        result = _row_to_message(row)

        self.assertIsInstance(result, HumanMessage)
        self.assertEqual(result.content, "Mystery content")


class TestDbServiceFetchAndDeleteOldMessages(unittest.IsolatedAsyncioTestCase):
    """Tests for DbService.fetch_and_delete_old_messages."""

    @patch("delpro_backend.db.db_service.AsyncSessionFactory")
    async def test_returns_empty_when_under_limit(self, mock_factory):
        """Test returns empty list when message count is under limit."""
        mock_session = AsyncMock()

        # Mock COUNT query (10 messages)
        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 10
        mock_session.execute.return_value = mock_count_result

        mock_factory.return_value.__aenter__.return_value = mock_session

        result = await DbService.fetch_and_delete_old_messages("session-1", 20)

        self.assertEqual(result, [])
        mock_session.commit.assert_not_awaited()

    @patch("delpro_backend.db.db_service.AsyncSessionFactory")
    async def test_fetches_and_deletes_old_messages(self, mock_factory):
        """Test fetches and deletes messages when over limit."""
        mock_session = AsyncMock()

        # Mock COUNT query (25 messages)
        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 25

        # Mock SELECT old messages (5 oldest)
        old_rows = [MagicMock(id=i, role="human", content=f"msg {i}") for i in range(1, 6)]
        mock_old_result = MagicMock()
        mock_old_result.scalars.return_value.all.return_value = old_rows

        mock_session.execute.side_effect = [
            mock_count_result,  # COUNT
            mock_old_result,  # SELECT old
            AsyncMock(),  # DELETE
        ]

        mock_factory.return_value.__aenter__.return_value = mock_session

        result = await DbService.fetch_and_delete_old_messages("session-1", 20)

        self.assertEqual(len(result), 5)
        self.assertIsInstance(result[0], HumanMessage)
        mock_session.commit.assert_awaited_once()

    @patch("delpro_backend.db.db_service.AsyncSessionFactory")
    async def test_returns_empty_when_no_rows_found(self, mock_factory):
        """Test returns empty list when old messages query returns no rows."""
        mock_session = AsyncMock()

        # Mock COUNT query (25 messages)
        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 25

        # Mock SELECT old messages (empty result)
        mock_old_result = MagicMock()
        mock_old_result.scalars.return_value.all.return_value = []

        mock_session.execute.side_effect = [
            mock_count_result,  # COUNT
            mock_old_result,  # SELECT old
        ]

        mock_factory.return_value.__aenter__.return_value = mock_session

        result = await DbService.fetch_and_delete_old_messages("session-1", 20)

        self.assertEqual(result, [])
        mock_session.commit.assert_not_awaited()


class TestDbServiceInsertSummaryMessage(unittest.IsolatedAsyncioTestCase):
    """Tests for DbService.insert_summary_message."""

    @patch("delpro_backend.db.db_service.AsyncSessionFactory")
    async def test_inserts_summary_message(self, mock_factory):
        """Test inserts SystemMessage with summary."""
        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_factory.return_value.__aenter__.return_value = mock_session

        await DbService.insert_summary_message("session-1", "Summary text")

        mock_session.add.assert_called_once()
        added_row = mock_session.add.call_args[0][0]
        self.assertEqual(added_row.session_id, "session-1")
        self.assertEqual(added_row.role, "system")
        self.assertEqual(added_row.content, "Summary text")
        mock_session.commit.assert_awaited_once()

    @patch("delpro_backend.db.db_service.AsyncSessionFactory")
    async def test_truncates_long_summary(self, mock_factory):
        """Test truncates summary text when too long."""
        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_factory.return_value.__aenter__.return_value = mock_session

        long_summary = "x" * 5000  # Longer than MAX_SUMMARY_LENGTH (4000)

        await DbService.insert_summary_message("session-1", long_summary)

        mock_session.add.assert_called_once()
        added_row = mock_session.add.call_args[0][0]
        self.assertEqual(len(added_row.content), 4003)  # 4000 + "..."
        self.assertTrue(added_row.content.endswith("..."))
        mock_session.commit.assert_awaited_once()
