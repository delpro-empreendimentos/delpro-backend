"""Tests for AssistantService."""

import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

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

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from delpro_backend.assistant.assistant_service import AssistantService
from delpro_backend.db.chat_history_service import PostgresChatMessageHistory


class TestAssistantServiceGetSessionHistory(unittest.TestCase):
    """Tests for _get_session_history."""

    def test_returns_postgres_chat_message_history(self):
        """Test that _get_session_history returns the correct type."""
        history = AssistantService._get_session_history("test-session")
        self.assertIsInstance(history, PostgresChatMessageHistory)

    def test_uses_correct_session_id(self):
        """Test that the returned history has the correct session_id."""
        history = AssistantService._get_session_history("my-session-123")
        self.assertEqual(history._session_id, "my-session-123")


class TestAssistantServiceChat(unittest.IsolatedAsyncioTestCase):
    """Tests for AssistantService.chat."""

    def setUp(self):
        """Reset the cached chain before each test."""
        AssistantService._chain_with_history = None

    @patch("delpro_backend.assistant.assistant_service.PostgresChatMessageHistory")
    @patch("delpro_backend.assistant.assistant_service.build_chat_prompt")
    @patch("delpro_backend.assistant.assistant_service.get_llm")
    async def test_chat_returns_response_content(
        self, mock_get_llm, mock_build_prompt, mock_history_class
    ):
        """Test that chat returns the content string from the LLM response."""
        # Mock history (empty)
        mock_history = AsyncMock()
        mock_history.aget_messages.return_value = []
        mock_history_class.return_value = mock_history

        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm

        mock_prompt = MagicMock()
        mock_build_prompt.return_value = mock_prompt

        mock_chain = AsyncMock()
        mock_chain.ainvoke.return_value = AIMessage(content="Hello! How can I help?")
        mock_prompt.__or__ = MagicMock(return_value=mock_chain)

        with patch(
            "delpro_backend.assistant.assistant_service.RunnableWithMessageHistory",
        ) as mock_rwmh:
            mock_rwmh_instance = AsyncMock()
            mock_rwmh_instance.ainvoke.return_value = AIMessage(content="Hello! How can I help?")
            mock_rwmh.return_value = mock_rwmh_instance

            result = await AssistantService.chat("session-1", "Hi there", "John Doe")

        self.assertEqual(result, "Hello! How can I help?")

    @patch("delpro_backend.assistant.assistant_service.PostgresChatMessageHistory")
    @patch("delpro_backend.assistant.assistant_service.build_chat_prompt")
    @patch("delpro_backend.assistant.assistant_service.get_llm")
    async def test_chat_passes_correct_config(
        self, mock_get_llm, mock_build_prompt, mock_history_class
    ):
        """Test that chat passes the correct session_id and context_info in config."""
        # Mock history (empty)
        mock_history = AsyncMock()
        mock_history.aget_messages.return_value = []
        mock_history_class.return_value = mock_history

        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm

        mock_prompt = MagicMock()
        mock_build_prompt.return_value = mock_prompt
        mock_prompt.__or__ = MagicMock(return_value=MagicMock())

        with patch(
            "delpro_backend.assistant.assistant_service.RunnableWithMessageHistory",
        ) as mock_rwmh:
            mock_rwmh_instance = AsyncMock()
            mock_rwmh_instance.ainvoke.return_value = AIMessage(content="response")
            mock_rwmh.return_value = mock_rwmh_instance

            await AssistantService.chat("session-42", "test message", "Alice")

            # Verify that ainvoke was called with input and context_info
            call_args = mock_rwmh_instance.ainvoke.call_args
            self.assertIn("input", call_args[0][0])
            self.assertIn("context_info", call_args[0][0])
            self.assertEqual(call_args[0][0]["input"], "test message")
            self.assertIn("Corretor: Alice", call_args[0][0]["context_info"])

    @patch("delpro_backend.assistant.assistant_service.PostgresChatMessageHistory")
    @patch("delpro_backend.assistant.assistant_service.build_chat_prompt")
    @patch("delpro_backend.assistant.assistant_service.get_llm")
    async def test_chat_handles_string_response(
        self, mock_get_llm, mock_build_prompt, mock_history_class
    ):
        """Test that chat handles a plain string response."""
        # Mock history (empty)
        mock_history = AsyncMock()
        mock_history.aget_messages.return_value = []
        mock_history_class.return_value = mock_history

        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm

        mock_prompt = MagicMock()
        mock_build_prompt.return_value = mock_prompt
        mock_prompt.__or__ = MagicMock(return_value=MagicMock())

        with patch(
            "delpro_backend.assistant.assistant_service.RunnableWithMessageHistory",
        ) as mock_rwmh:
            mock_rwmh_instance = AsyncMock()
            mock_rwmh_instance.ainvoke.return_value = "plain string"
            mock_rwmh.return_value = mock_rwmh_instance

            result = await AssistantService.chat("session-1", "hello", "Bob")

        self.assertEqual(result, "plain string")

    @patch("delpro_backend.assistant.assistant_service.PostgresChatMessageHistory")
    @patch("delpro_backend.assistant.assistant_service.build_chat_prompt")
    @patch("delpro_backend.assistant.assistant_service.get_llm")
    async def test_chat_includes_context_summary(
        self, mock_get_llm, mock_build_prompt, mock_history_class
    ):
        """Test that context summary from SystemMessage is included in context_info."""
        # Mock history with SystemMessage (summary)
        mock_history = AsyncMock()
        mock_history.aget_messages.return_value = [
            HumanMessage(content="Mensagem antiga"),
            AIMessage(content="Resposta antiga"),
            SystemMessage(content="Resumo: Cliente interessado em apartamento 2 quartos"),
        ]
        mock_history_class.return_value = mock_history

        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm

        mock_prompt = MagicMock()
        mock_build_prompt.return_value = mock_prompt
        mock_prompt.__or__ = MagicMock(return_value=MagicMock())

        with patch(
            "delpro_backend.assistant.assistant_service.RunnableWithMessageHistory",
        ) as mock_rwmh:
            mock_rwmh_instance = AsyncMock()
            mock_rwmh_instance.ainvoke.return_value = AIMessage(content="Resposta")
            mock_rwmh.return_value = mock_rwmh_instance

            await AssistantService.chat("test", "Ola", "Joao")

            # Verify context_info includes summary
            call_args = mock_rwmh_instance.ainvoke.call_args
            context_info = call_args[0][0]["context_info"]
            self.assertIn("Contexto anterior", context_info)
            self.assertIn("apartamento 2 quartos", context_info)

    @patch("delpro_backend.assistant.assistant_service.PostgresChatMessageHistory")
    @patch("delpro_backend.assistant.assistant_service.build_chat_prompt")
    @patch("delpro_backend.assistant.assistant_service.get_llm")
    async def test_chat_handles_list_with_non_dict_items(
        self, mock_get_llm, mock_build_prompt, mock_history_class
    ):
        """Test chat handles response with list containing non-dict items."""
        # Mock history (empty)
        mock_history = AsyncMock()
        mock_history.aget_messages.return_value = []
        mock_history_class.return_value = mock_history

        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm

        mock_prompt = MagicMock()
        mock_build_prompt.return_value = mock_prompt
        mock_prompt.__or__ = MagicMock(return_value=MagicMock())

        with patch(
            "delpro_backend.assistant.assistant_service.RunnableWithMessageHistory",
        ) as mock_rwmh:
            mock_rwmh_instance = AsyncMock()
            # Response with list of non-dict items (strings)
            mock_response = MagicMock()
            mock_response.content = ["text item", "another item"]
            mock_rwmh_instance.ainvoke.return_value = mock_response
            mock_rwmh.return_value = mock_rwmh_instance

            result = await AssistantService.chat("session-1", "hello", "Bob")

        self.assertEqual(result, "text item")

    @patch("delpro_backend.assistant.assistant_service.PostgresChatMessageHistory")
    @patch("delpro_backend.assistant.assistant_service.build_chat_prompt")
    @patch("delpro_backend.assistant.assistant_service.get_llm")
    async def test_chat_handles_non_string_non_list_content(
        self, mock_get_llm, mock_build_prompt, mock_history_class
    ):
        """Test chat handles response with content that is neither string nor list."""
        # Mock history (empty)
        mock_history = AsyncMock()
        mock_history.aget_messages.return_value = []
        mock_history_class.return_value = mock_history

        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm

        mock_prompt = MagicMock()
        mock_build_prompt.return_value = mock_prompt
        mock_prompt.__or__ = MagicMock(return_value=MagicMock())

        with patch(
            "delpro_backend.assistant.assistant_service.RunnableWithMessageHistory",
        ) as mock_rwmh:
            mock_rwmh_instance = AsyncMock()
            # Response with non-string, non-list content (e.g., int)
            mock_response = MagicMock()
            mock_response.content = 12345
            mock_rwmh_instance.ainvoke.return_value = mock_response
            mock_rwmh.return_value = mock_rwmh_instance

            result = await AssistantService.chat("session-1", "hello", "Bob")

        self.assertEqual(result, "12345")

    @patch("delpro_backend.assistant.assistant_service.PostgresChatMessageHistory")
    @patch("delpro_backend.assistant.assistant_service.build_chat_prompt")
    @patch("delpro_backend.assistant.assistant_service.get_llm")
    async def test_chat_handles_dict_without_text_key(
        self, mock_get_llm, mock_build_prompt, mock_history_class
    ):
        """Test chat handles response with dict that doesn't have a 'text' key."""
        # Mock history (empty)
        mock_history = AsyncMock()
        mock_history.aget_messages.return_value = []
        mock_history_class.return_value = mock_history

        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm

        mock_prompt = MagicMock()
        mock_build_prompt.return_value = mock_prompt
        mock_prompt.__or__ = MagicMock(return_value=MagicMock())

        with patch(
            "delpro_backend.assistant.assistant_service.RunnableWithMessageHistory",
        ) as mock_rwmh:
            mock_rwmh_instance = AsyncMock()
            # Response with dict list but no "text" key - should use fallback
            mock_response = MagicMock()
            mock_response.content = [{"type": "image", "data": "base64data"}]
            mock_rwmh_instance.ainvoke.return_value = mock_response
            mock_rwmh.return_value = mock_rwmh_instance

            result = await AssistantService.chat("session-1", "hello", "Bob")

        # Should use the fallback str(content)
        self.assertIn("type", result)
        self.assertIn("image", result)

    @patch("delpro_backend.assistant.assistant_service.PostgresChatMessageHistory")
    @patch("delpro_backend.assistant.assistant_service.build_chat_prompt")
    @patch("delpro_backend.assistant.assistant_service.get_llm")
    async def test_chat_finds_system_message_in_history(
        self, mock_get_llm, mock_build_prompt, mock_history_class
    ):
        """Test that chat iterates through history to find SystemMessage."""
        # Mock history with multiple messages, SystemMessage not at the end
        mock_history = AsyncMock()
        mock_history.aget_messages.return_value = [
            HumanMessage(content="Old question 1"),
            AIMessage(content="Old response 1"),
            SystemMessage(content="Summary of old conversation"),
            HumanMessage(content="Old question 2"),
            AIMessage(content="Old response 2"),
        ]
        mock_history_class.return_value = mock_history

        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm

        mock_prompt = MagicMock()
        mock_build_prompt.return_value = mock_prompt
        mock_prompt.__or__ = MagicMock(return_value=MagicMock())

        with patch(
            "delpro_backend.assistant.assistant_service.RunnableWithMessageHistory",
        ) as mock_rwmh:
            mock_rwmh_instance = AsyncMock()
            mock_rwmh_instance.ainvoke.return_value = AIMessage(content="Response")
            mock_rwmh.return_value = mock_rwmh_instance

            await AssistantService.chat("test", "New question", "Alice")

            # Verify that context_info includes the summary
            call_args = mock_rwmh_instance.ainvoke.call_args
            context_info = call_args[0][0]["context_info"]
            self.assertIn("Contexto anterior", context_info)
            self.assertIn("Summary of old conversation", context_info)


class TestAssistantServiceGetChain(unittest.TestCase):
    """Tests for _get_chain caching."""

    def setUp(self):
        """Reset the cached chain before each test."""
        AssistantService._chain_with_history = None

    @patch("delpro_backend.assistant.assistant_service.build_chat_prompt")
    @patch("delpro_backend.assistant.assistant_service.get_llm")
    @patch("delpro_backend.assistant.assistant_service.RunnableWithMessageHistory")
    def test_get_chain_caches(self, mock_rwmh, mock_get_llm, mock_build_prompt):
        """Test that _get_chain returns the same instance on subsequent calls."""
        mock_build_prompt.return_value = MagicMock()
        mock_build_prompt.return_value.__or__ = MagicMock(return_value=MagicMock())
        mock_get_llm.return_value = MagicMock()
        mock_rwmh.return_value = MagicMock()

        chain1 = AssistantService._get_chain()
        chain2 = AssistantService._get_chain()

        self.assertIs(chain1, chain2)
        mock_rwmh.assert_called_once()
