"""Tests for PostgresChatMessageHistory."""

import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from delpro_backend.db.chat_history_service import (
    PostgresChatMessageHistory,
    _message_to_role,
    _row_to_message,
)
from delpro_backend.db.models import MessageRow
from tests.keys_test import DEFAULT_KEYS

for key, value in DEFAULT_KEYS.items():
    os.environ.setdefault(key, value)


class TestRowToMessage(unittest.TestCase):
    """Tests for the _row_to_message converter."""

    def _make_row(self, role: str, content: str) -> MagicMock:
        row = MagicMock(spec=MessageRow)
        row.role = role
        row.content = content
        return row

    def test_human_role(self):
        """Test conversion of human role to HumanMessage."""
        msg = _row_to_message(self._make_row("human", "hello"))
        self.assertIsInstance(msg, HumanMessage)
        self.assertEqual(msg.content, "hello")

    def test_ai_role(self):
        """Test conversion of ai role to AIMessage."""
        msg = _row_to_message(self._make_row("ai", "response"))
        self.assertIsInstance(msg, AIMessage)
        self.assertEqual(msg.content, "response")

    def test_system_role(self):
        """Test conversion of system role to SystemMessage."""
        msg = _row_to_message(self._make_row("system", "instructions"))
        self.assertIsInstance(msg, SystemMessage)
        self.assertEqual(msg.content, "instructions")

    def test_unknown_role_defaults_to_human(self):
        """Test that unknown roles default to HumanMessage."""
        msg = _row_to_message(self._make_row("unknown", "text"))
        self.assertIsInstance(msg, HumanMessage)
        self.assertEqual(msg.content, "text")


class TestMessageToRole(unittest.TestCase):
    """Tests for the _message_to_role converter."""

    def test_human_message(self):
        """Test HumanMessage maps to 'human'."""
        self.assertEqual(_message_to_role(HumanMessage(content="hi")), "human")

    def test_ai_message(self):
        """Test AIMessage maps to 'ai'."""
        self.assertEqual(_message_to_role(AIMessage(content="resp")), "ai")

    def test_system_message(self):
        """Test SystemMessage maps to 'system'."""
        self.assertEqual(_message_to_role(SystemMessage(content="sys")), "system")

    def test_unknown_message_defaults_to_human(self):
        """Test that unknown message types default to 'human'."""
        from langchain_core.messages import ChatMessage

        self.assertEqual(_message_to_role(ChatMessage(content="x", role="custom")), "human")


class TestPostgresChatMessageHistorySync(unittest.TestCase):
    """Tests for sync methods that should raise NotImplementedError."""

    def setUp(self):
        """Set up a PostgresChatMessageHistory instance."""
        self.history = PostgresChatMessageHistory(
            session_id="test-session",
            async_session_factory=MagicMock(),
        )

    def test_messages_property_raises(self):
        """Test that sync messages property raises NotImplementedError."""
        with self.assertRaises(NotImplementedError):
            _ = self.history.messages

    def test_clear_raises(self):
        """Test that sync clear raises NotImplementedError."""
        with self.assertRaises(NotImplementedError):
            self.history.clear()


class TestPostgresChatMessageHistoryAsync(unittest.IsolatedAsyncioTestCase):
    """Tests for async methods of PostgresChatMessageHistory."""

    def _make_mock_factory(self, mock_session: AsyncMock) -> MagicMock:
        """Create a mock async session factory."""
        factory = MagicMock()
        factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        factory.return_value.__aexit__ = AsyncMock(return_value=False)
        return factory

    async def test_aget_messages_empty(self):
        """Test aget_messages returns empty list for new session."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        factory = self._make_mock_factory(mock_session)
        history = PostgresChatMessageHistory(
            session_id="empty-session", async_session_factory=factory
        )

        messages = await history.aget_messages()
        self.assertEqual(messages, [])

    async def test_aget_messages_returns_correct_types(self):
        """Test aget_messages returns correctly typed messages."""
        row_human = MagicMock(spec=MessageRow)
        row_human.role = "human"
        row_human.content = "hello"

        row_ai = MagicMock(spec=MessageRow)
        row_ai.role = "ai"
        row_ai.content = "hi there"

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [row_human, row_ai]
        mock_session.execute.return_value = mock_result

        factory = self._make_mock_factory(mock_session)
        history = PostgresChatMessageHistory(session_id="test", async_session_factory=factory)

        messages = await history.aget_messages()
        self.assertEqual(len(messages), 2)
        self.assertIsInstance(messages[0], HumanMessage)
        self.assertIsInstance(messages[1], AIMessage)

    async def test_aadd_messages_persists(self):
        """Test aadd_messages persists messages and commits."""
        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        factory = self._make_mock_factory(mock_session)

        history = PostgresChatMessageHistory(session_id="test", async_session_factory=factory)

        await history.aadd_messages(
            [
                HumanMessage(content="hello"),
                AIMessage(content="hi"),
            ]
        )

        self.assertEqual(mock_session.add.call_count, 2)
        mock_session.commit.assert_awaited_once()

    async def test_aclear_deletes_messages(self):
        """Test aclear deletes all messages for the session."""
        row1 = MagicMock(spec=MessageRow)
        row2 = MagicMock(spec=MessageRow)

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [row1, row2]
        mock_session.execute.return_value = mock_result

        factory = self._make_mock_factory(mock_session)
        history = PostgresChatMessageHistory(session_id="test", async_session_factory=factory)

        await history.aclear()

        self.assertEqual(mock_session.delete.await_count, 2)
        mock_session.commit.assert_awaited_once()


class TestSummarization(unittest.IsolatedAsyncioTestCase):
    """Tests for auto-summarization logic."""

    def _make_mock_factory(self, mock_session):
        factory = MagicMock()
        factory.return_value.__aenter__.return_value = mock_session
        factory.return_value.__aexit__.return_value = AsyncMock()
        return factory

    @patch("delpro_backend.db.chat_history_service.DbService.insert_summary_message")
    @patch("delpro_backend.db.chat_history_service.DbService.fetch_and_delete_old_messages")
    @patch("delpro_backend.db.chat_history_service.get_summary_llm")
    async def test_summarization_with_old_messages(
        self, mock_get_llm, mock_fetch_delete, mock_insert_summary
    ):
        """Test that summarization works when there are old messages."""
        # Mock old messages returned by DbService
        old_messages = [
            HumanMessage(content="Hello"),
            AIMessage(content="Hi there!"),
        ]
        mock_fetch_delete.return_value = old_messages

        # Mock LLM response
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = AIMessage(content="Summary: User greeted assistant")
        mock_get_llm.return_value = mock_llm

        # Create history
        mock_session = AsyncMock()
        factory = self._make_mock_factory(mock_session)
        history = PostgresChatMessageHistory(session_id="test", async_session_factory=factory)

        # Call summarization
        await history._asummarize_old_messages()

        # Verify DbService was called
        mock_fetch_delete.assert_awaited_once()
        mock_insert_summary.assert_awaited_once()

        # Verify summary was generated
        mock_llm.ainvoke.assert_awaited_once()

    @patch("delpro_backend.db.chat_history_service.DbService.fetch_and_delete_old_messages")
    async def test_summarization_with_no_old_messages(self, mock_fetch_delete):
        """Test that summarization skips when no old messages."""
        # Mock no old messages
        mock_fetch_delete.return_value = []

        # Create history
        mock_session = AsyncMock()
        factory = self._make_mock_factory(mock_session)
        history = PostgresChatMessageHistory(session_id="test", async_session_factory=factory)

        # Call summarization
        await history._asummarize_old_messages()

        # Verify DbService was called
        mock_fetch_delete.assert_awaited_once()

        # No further processing should happen (LLM not called)

    @patch("delpro_backend.db.chat_history_service.DbService.insert_summary_message")
    @patch("delpro_backend.db.chat_history_service.DbService.fetch_and_delete_old_messages")
    @patch("delpro_backend.db.chat_history_service.get_summary_llm")
    async def test_summarization_handles_llm_failure(
        self, mock_get_llm, mock_fetch_delete, mock_insert_summary
    ):
        """Test that summarization handles LLM failures gracefully."""
        # Mock old messages
        old_messages = [HumanMessage(content="Hello")]
        mock_fetch_delete.return_value = old_messages

        # Mock LLM to raise exception
        mock_llm = AsyncMock()
        mock_llm.ainvoke.side_effect = Exception("LLM API unavailable")
        mock_get_llm.return_value = mock_llm

        # Create history
        mock_session = AsyncMock()
        factory = self._make_mock_factory(mock_session)
        history = PostgresChatMessageHistory(session_id="test", async_session_factory=factory)

        # Call summarization - should not raise
        await history._asummarize_old_messages()

        # Verify fetch was called but insert was not (due to error)
        mock_fetch_delete.assert_awaited_once()
        mock_insert_summary.assert_not_awaited()

    @patch("delpro_backend.db.chat_history_service.DbService.insert_summary_message")
    @patch("delpro_backend.db.chat_history_service.DbService.fetch_and_delete_old_messages")
    @patch("delpro_backend.db.chat_history_service.get_summary_llm")
    async def test_summarization_with_list_non_dict_content(
        self, mock_get_llm, mock_fetch_delete, mock_insert_summary
    ):
        """Test summarization handles LLM response with list of non-dict items."""
        old_messages = [HumanMessage(content="Hello")]
        mock_fetch_delete.return_value = old_messages

        # Mock LLM response with list of strings
        mock_llm = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = ["Summary text", "more text"]
        mock_llm.ainvoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm

        mock_session = AsyncMock()
        factory = self._make_mock_factory(mock_session)
        history = PostgresChatMessageHistory(session_id="test", async_session_factory=factory)

        await history._asummarize_old_messages()

        # Verify summary was inserted with first item as string
        mock_insert_summary.assert_awaited_once()
        call_args = mock_insert_summary.call_args
        self.assertEqual(call_args[0][1], "Summary text")

    @patch("delpro_backend.db.chat_history_service.DbService.insert_summary_message")
    @patch("delpro_backend.db.chat_history_service.DbService.fetch_and_delete_old_messages")
    @patch("delpro_backend.db.chat_history_service.get_summary_llm")
    async def test_summarization_with_non_string_non_list_content(
        self, mock_get_llm, mock_fetch_delete, mock_insert_summary
    ):
        """Test summarization handles LLM response with non-string, non-list content."""
        old_messages = [HumanMessage(content="Hello")]
        mock_fetch_delete.return_value = old_messages

        # Mock LLM response with non-string, non-list content
        mock_llm = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = 12345
        mock_llm.ainvoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm

        mock_session = AsyncMock()
        factory = self._make_mock_factory(mock_session)
        history = PostgresChatMessageHistory(session_id="test", async_session_factory=factory)

        await history._asummarize_old_messages()

        # Verify summary was inserted with stringified content
        mock_insert_summary.assert_awaited_once()
        call_args = mock_insert_summary.call_args
        self.assertEqual(call_args[0][1], "12345")

    @patch("delpro_backend.db.chat_history_service.DbService.insert_summary_message")
    @patch("delpro_backend.db.chat_history_service.DbService.fetch_and_delete_old_messages")
    @patch("delpro_backend.db.chat_history_service.get_summary_llm")
    async def test_summarization_with_no_content_attribute(
        self, mock_get_llm, mock_fetch_delete, mock_insert_summary
    ):
        """Test summarization handles LLM response without content attribute."""
        old_messages = [HumanMessage(content="Hello")]
        mock_fetch_delete.return_value = old_messages

        # Mock LLM response without content attribute
        mock_llm = AsyncMock()
        mock_response = "plain string response"
        mock_llm.ainvoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm

        mock_session = AsyncMock()
        factory = self._make_mock_factory(mock_session)
        history = PostgresChatMessageHistory(session_id="test", async_session_factory=factory)

        await history._asummarize_old_messages()

        # Verify summary was inserted with stringified response
        mock_insert_summary.assert_awaited_once()
        call_args = mock_insert_summary.call_args
        self.assertEqual(call_args[0][1], "plain string response")

    @patch("delpro_backend.db.chat_history_service.DbService.insert_summary_message")
    @patch("delpro_backend.db.chat_history_service.DbService.fetch_and_delete_old_messages")
    @patch("delpro_backend.db.chat_history_service.get_summary_llm")
    async def test_summarization_with_dict_without_text_key(
        self, mock_get_llm, mock_fetch_delete, mock_insert_summary
    ):
        """Test summarization handles dict without 'text' key."""
        old_messages = [HumanMessage(content="Hello")]
        mock_fetch_delete.return_value = old_messages

        # Mock LLM response with dict list but no "text" key
        mock_llm = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = [{"type": "other", "data": "value"}]
        mock_llm.ainvoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm

        mock_session = AsyncMock()
        factory = self._make_mock_factory(mock_session)
        history = PostgresChatMessageHistory(session_id="test", async_session_factory=factory)

        await history._asummarize_old_messages()

        # Verify summary was inserted with fallback str(content)
        mock_insert_summary.assert_awaited_once()
        call_args = mock_insert_summary.call_args
        summary = call_args[0][1]
        self.assertIn("type", summary)
        self.assertIn("other", summary)
