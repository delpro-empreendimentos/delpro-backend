"""Tests for AssistantService."""

import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from tests.keys_test import DEFAULT_KEYS

for key, value in DEFAULT_KEYS.items():
    os.environ.setdefault(key, value)

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage  # noqa: E402

from delpro_backend.assistant.assistant_service import AssistantService  # noqa: E402
from delpro_backend.db.chat_history_service import PostgresChatMessageHistory  # noqa: E402


def _make_service():
    """Create AssistantService with fully mocked dependencies."""
    mock_llm = MagicMock()
    mock_llm.bind_tools.return_value = MagicMock()
    mock_rag = MagicMock()
    mock_media = MagicMock()
    with patch("delpro_backend.assistant.assistant_service.build_tools", return_value=[]):
        return AssistantService(
            rag_service=mock_rag, llm=mock_llm, media_service=mock_media
        )


class TestAssistantServiceGetSessionHistory(unittest.TestCase):
    """Tests for _get_session_history."""

    def test_returns_postgres_chat_message_history(self):
        """Test that _get_session_history returns the correct type."""
        svc = _make_service()
        history = svc._get_session_history("test-session")
        self.assertIsInstance(history, PostgresChatMessageHistory)

    def test_uses_correct_session_id(self):
        """Test that the returned history has the correct session_id."""
        svc = _make_service()
        history = svc._get_session_history("my-session-123")
        self.assertEqual(history._session_id, "my-session-123")


class TestAssistantServiceExtractText(unittest.TestCase):
    """Tests for _extract_text static method."""

    def test_extracts_string_content(self):
        """Test extraction from a response with string content."""
        response = MagicMock()
        response.content = "Hello world"
        self.assertEqual(AssistantService._extract_text(response), "Hello world")

    def test_extracts_list_dict_with_text_key(self):
        """Test extraction from list of dicts with 'text' key."""
        response = MagicMock()
        response.content = [{"type": "text", "text": "Answer"}]
        self.assertEqual(AssistantService._extract_text(response), "Answer")

    def test_extracts_list_dict_without_text_key(self):
        """Test extraction from list of dicts without 'text' key falls back to str."""
        response = MagicMock()
        response.content = [{"type": "image", "data": "base64"}]
        result = AssistantService._extract_text(response)
        self.assertIn("type", result)

    def test_extracts_list_non_dict(self):
        """Test extraction from list of non-dict items uses first item as str."""
        response = MagicMock()
        response.content = ["plain text", "second"]
        self.assertEqual(AssistantService._extract_text(response), "plain text")

    def test_extracts_empty_list(self):
        """Test extraction from empty list returns fallback message."""
        response = MagicMock()
        response.content = []
        result = AssistantService._extract_text(response)
        self.assertEqual(result, "Desculpe, não consegui gerar uma resposta. Pode repetir?")

    def test_extracts_non_string_non_list_content(self):
        """Test extraction from non-string, non-list content uses str()."""
        response = MagicMock()
        response.content = 12345
        self.assertEqual(AssistantService._extract_text(response), "12345")

    def test_fallback_when_no_content_attribute(self):
        """Test fallback to str(response) when no content attribute."""
        result = AssistantService._extract_text("plain string")
        self.assertEqual(result, "plain string")


class TestAssistantServiceExecuteTools(unittest.IsolatedAsyncioTestCase):
    """Tests for _execute_tools."""

    def _make_ai_message(self, tool_calls):
        msg = MagicMock(spec=AIMessage)
        msg.tool_calls = tool_calls
        return msg

    async def test_executes_known_tool(self):
        """Test that a known tool is invoked and returns a ToolMessage."""
        svc = _make_service()
        mock_tool = AsyncMock()
        mock_tool.ainvoke = AsyncMock(return_value="tool result")
        svc._tools_by_name = {"my_tool": mock_tool}

        tool_calls = [{"name": "my_tool", "args": {"q": "hello"}, "id": "call-1"}]
        ai_msg = self._make_ai_message(tool_calls)

        results = await svc._execute_tools(ai_msg)

        self.assertEqual(len(results), 1)
        self.assertIsInstance(results[0], ToolMessage)
        self.assertEqual(results[0].content, "tool result")

    async def test_unknown_tool_returns_error_message(self):
        """Test that an unknown tool returns an error ToolMessage."""
        svc = _make_service()
        svc._tools_by_name = {}

        tool_calls = [{"name": "ghost_tool", "args": {}, "id": "call-2"}]
        ai_msg = self._make_ai_message(tool_calls)

        results = await svc._execute_tools(ai_msg)

        self.assertEqual(len(results), 1)
        self.assertIn("ghost_tool", results[0].content)

    async def test_tool_exception_returns_error_message(self):
        """Test that a tool that raises an exception returns an error ToolMessage."""
        svc = _make_service()
        mock_tool = AsyncMock()
        mock_tool.ainvoke = AsyncMock(side_effect=RuntimeError("boom"))
        svc._tools_by_name = {"fail_tool": mock_tool}

        tool_calls = [{"name": "fail_tool", "args": {}, "id": "call-3"}]
        ai_msg = self._make_ai_message(tool_calls)

        results = await svc._execute_tools(ai_msg)

        self.assertEqual(len(results), 1)
        self.assertIn("fail_tool", results[0].content)

    async def test_multiple_tools_parallel(self):
        """Test that multiple tools are executed and all return ToolMessages."""
        svc = _make_service()
        tool_a = AsyncMock()
        tool_a.ainvoke = AsyncMock(return_value="result_a")
        tool_b = AsyncMock()
        tool_b.ainvoke = AsyncMock(return_value="result_b")
        svc._tools_by_name = {"tool_a": tool_a, "tool_b": tool_b}

        tool_calls = [
            {"name": "tool_a", "args": {}, "id": "id-a"},
            {"name": "tool_b", "args": {}, "id": "id-b"},
        ]
        ai_msg = self._make_ai_message(tool_calls)

        results = await svc._execute_tools(ai_msg)

        self.assertEqual(len(results), 2)
        contents = {r.content for r in results}
        self.assertIn("result_a", contents)
        self.assertIn("result_b", contents)


class TestLoadPromptTemplate(unittest.IsolatedAsyncioTestCase):
    """Tests for _load_prompt_template."""

    async def test_loads_from_db_when_row_exists(self):
        """When a PromptRow exists, build prompt from its content."""
        svc = _make_service()

        mock_row = MagicMock()
        mock_row.content = "Custom system prompt"

        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=mock_row)
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("delpro_backend.assistant.assistant_service.AsyncSessionFactory", return_value=mock_ctx),
            patch(
                "delpro_backend.assistant.assistant_service.build_chat_prompt_from_text"
            ) as mock_from_text,
            patch("delpro_backend.assistant.assistant_service.build_chat_prompt") as mock_yaml,
        ):
            await svc._load_prompt_template()

        mock_from_text.assert_called_once_with("Custom system prompt")
        mock_yaml.assert_not_called()

    async def test_falls_back_to_yaml_when_no_row(self):
        """When no PromptRow exists, fall back to build_chat_prompt (YAML)."""
        svc = _make_service()

        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=None)
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("delpro_backend.assistant.assistant_service.AsyncSessionFactory", return_value=mock_ctx),
            patch(
                "delpro_backend.assistant.assistant_service.build_chat_prompt_from_text"
            ) as mock_from_text,
            patch("delpro_backend.assistant.assistant_service.build_chat_prompt") as mock_yaml,
        ):
            await svc._load_prompt_template()

        mock_yaml.assert_called_once()
        mock_from_text.assert_not_called()


class TestAssistantServiceChat(unittest.IsolatedAsyncioTestCase):
    """Tests for AssistantService.chat."""

    def _make_service_with_mocks(self):
        """Return (svc, mock_llm_with_tools, mock_history_store)."""
        svc = _make_service()

        mock_history = AsyncMock(spec=PostgresChatMessageHistory)
        mock_history.aget_messages = AsyncMock(return_value=[])
        mock_history.aadd_messages = AsyncMock()

        mock_prompt_value = MagicMock()
        mock_prompt_value.to_messages.return_value = [HumanMessage(content="hi")]

        mock_prompt_template = AsyncMock()
        mock_prompt_template.ainvoke = AsyncMock(return_value=mock_prompt_value)

        svc._get_session_history = MagicMock(return_value=mock_history)
        svc._load_prompt_template = AsyncMock(return_value=mock_prompt_template)

        return svc, svc._llm_with_tools, mock_history, mock_prompt_template

    async def test_chat_no_tool_calls_returns_text(self):
        """When LLM returns no tool_calls, extract text and save history."""
        svc, mock_llm_with_tools, mock_history, _ = self._make_service_with_mocks()

        ai_response = MagicMock(spec=AIMessage)
        ai_response.content = "Hello!"
        ai_response.tool_calls = []
        mock_llm_with_tools.ainvoke = AsyncMock(return_value=ai_response)

        result = await svc.chat(
            sender_phone_number="5511999",
            user_message="Hi",
            user_name="Alice",
        )

        self.assertEqual(result, "Hello!")
        mock_history.aadd_messages.assert_awaited_once()

    async def test_chat_with_tool_calls_does_round2(self):
        """When LLM returns tool_calls, execute tools then call LLM again."""
        svc, mock_llm_with_tools, mock_history, _ = self._make_service_with_mocks()

        ai_round1 = MagicMock(spec=AIMessage)
        ai_round1.content = ""
        ai_round1.tool_calls = [{"name": "my_tool", "args": {}, "id": "c1"}]

        ai_round2 = MagicMock(spec=AIMessage)
        ai_round2.content = "Final answer"
        ai_round2.tool_calls = []

        mock_llm_with_tools.ainvoke = AsyncMock(side_effect=[ai_round1, ai_round2])

        mock_tool = AsyncMock()
        mock_tool.ainvoke = AsyncMock(return_value="tool result")
        svc._tools_by_name = {"my_tool": mock_tool}

        result = await svc.chat(
            sender_phone_number="5511999",
            user_message="Send me something",
            user_name="Bob",
        )

        self.assertEqual(result, "Final answer")
        self.assertEqual(mock_llm_with_tools.ainvoke.await_count, 2)
        mock_history.aadd_messages.assert_awaited_once()

    async def test_chat_saves_human_and_ai_messages(self):
        """Verify that both HumanMessage and AIMessage are saved after no-tool response."""
        svc, mock_llm_with_tools, mock_history, _ = self._make_service_with_mocks()

        ai_response = MagicMock(spec=AIMessage)
        ai_response.content = "My answer"
        ai_response.tool_calls = []
        mock_llm_with_tools.ainvoke = AsyncMock(return_value=ai_response)

        await svc.chat(
            sender_phone_number="123",
            user_message="Question",
            user_name="Carlos",
        )

        saved = mock_history.aadd_messages.call_args[0][0]
        roles = [type(m).__name__ for m in saved]
        self.assertIn("HumanMessage", roles)
        self.assertIn("AIMessage", roles)

    async def test_chat_with_existing_history(self):
        """Chat should load and pass existing history to the prompt."""
        svc, mock_llm_with_tools, mock_history, mock_prompt_template = self._make_service_with_mocks()

        existing = [HumanMessage(content="old"), AIMessage(content="old reply")]
        mock_history.aget_messages = AsyncMock(return_value=existing)

        ai_response = MagicMock(spec=AIMessage)
        ai_response.content = "New answer"
        ai_response.tool_calls = []
        mock_llm_with_tools.ainvoke = AsyncMock(return_value=ai_response)

        result = await svc.chat("999", "New question", "Dave")

        self.assertEqual(result, "New answer")
        prompt_call = mock_prompt_template.ainvoke.call_args[0][0]
        self.assertEqual(prompt_call["history"], existing)

    async def test_clear_history_calls_aclear(self):
        """clear_history should delegate to the history store's aclear method."""
        svc, _, mock_history, _ = self._make_service_with_mocks()
        mock_history.aclear = AsyncMock()

        await svc.clear_history("5511999")

        mock_history.aclear.assert_awaited_once()


