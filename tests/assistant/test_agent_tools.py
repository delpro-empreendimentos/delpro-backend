"""Tests for agent_tools.build_tools."""

import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from tests.keys_test import DEFAULT_KEYS

for key, value in DEFAULT_KEYS.items():
    os.environ.setdefault(key, value)

from delpro_backend.assistant.agent_tools import build_tools  # noqa: E402


def _make_services(rag_result=None, media_result=None):
    """Create mock RAGService and MediaService."""
    mock_rag = MagicMock()
    mock_rag.retrieve_context = AsyncMock(return_value=rag_result)

    mock_media = MagicMock()
    mock_media.search_media_by_description = AsyncMock(return_value=media_result)

    return mock_rag, mock_media


class TestBuildTools(unittest.TestCase):
    """Tests for build_tools factory."""

    def test_returns_two_tools(self):
        """Test that build_tools returns exactly two tools."""
        mock_rag, mock_media = _make_services()
        tools = build_tools(mock_rag, mock_media)
        self.assertEqual(len(tools), 2)

    def test_tool_names(self):
        """Test that both tools have the expected names."""
        mock_rag, mock_media = _make_services()
        tools = build_tools(mock_rag, mock_media)
        names = {t.name for t in tools}
        self.assertIn("search_knowledge_base", names)
        self.assertIn("send_whatsapp_media", names)


class TestSearchKnowledgeBase(unittest.IsolatedAsyncioTestCase):
    """Tests for search_knowledge_base tool."""

    def _get_tool(self, rag_result=None):
        mock_rag, mock_media = _make_services(rag_result=rag_result)
        tools = build_tools(mock_rag, mock_media)
        tool = next(t for t in tools if t.name == "search_knowledge_base")
        return tool, mock_rag

    async def test_returns_context_when_found(self):
        """Test that found context is returned as-is."""
        tool, mock_rag = self._get_tool(rag_result="Delpro property info")
        result = await tool.ainvoke({"query": "property info"})
        self.assertEqual(result, "Delpro property info")
        mock_rag.retrieve_context.assert_awaited_once_with("property info")

    async def test_returns_not_found_message_when_none(self):
        """Test that None result returns a fallback message."""
        tool, mock_rag = self._get_tool(rag_result=None)
        result = await tool.ainvoke({"query": "unknown query"})
        self.assertEqual(result, "No relevant information found in the documents.")

    async def test_returns_not_found_message_when_empty_string(self):
        """Test that empty-string result returns a fallback message."""
        tool, mock_rag = self._get_tool(rag_result="")
        result = await tool.ainvoke({"query": "empty"})
        self.assertEqual(result, "No relevant information found in the documents.")


class TestSendWhatsappMedia(unittest.IsolatedAsyncioTestCase):
    """Tests for send_whatsapp_media tool."""

    def _get_tool(self, media_results=None):
        mock_rag, mock_media = _make_services()
        if media_results is not None:
            mock_media.search_media_by_description = AsyncMock(side_effect=media_results)
        tools = build_tools(mock_rag, mock_media)
        tool = next(t for t in tools if t.name == "send_whatsapp_media")
        return tool, mock_media

    @patch("delpro_backend.assistant.agent_tools.whatsapp_api.upload_media", new_callable=AsyncMock)
    async def test_sends_media_when_found(self, mock_upload):
        """Test that found media files are uploaded and sent."""
        mock_item = MagicMock()
        mock_item.file_content = b"\xff\xd8\xff" + b"x" * 100
        mock_item.content_type = "image/jpeg"
        mock_item.filename = "photo.jpg"

        tool, mock_media = self._get_tool(media_results=[mock_item])

        result = await tool.ainvoke({"phone_number": "5511999", "queries": ["pool photo"]})

        mock_upload.assert_awaited_once_with(
            mock_item.file_content,
            mock_item.content_type,
            mock_item.filename,
            phone_number="5511999",
        )
        self.assertIn("Sent 1 media file(s) to 5511999", result)

    @patch("delpro_backend.assistant.agent_tools.whatsapp_api.upload_media", new_callable=AsyncMock)
    async def test_returns_not_found_when_all_missing(self, mock_upload):
        """Test that message is returned when no media match."""
        tool, mock_media = self._get_tool(media_results=[None])

        result = await tool.ainvoke({"phone_number": "5511999", "queries": ["nothing"]})

        mock_upload.assert_not_awaited()
        self.assertIn("No matching media found", result)

    @patch("delpro_backend.assistant.agent_tools.whatsapp_api.upload_media", new_callable=AsyncMock)
    async def test_partial_match_reports_not_found(self, mock_upload):
        """Test that partial matches report which descriptions had no media."""
        mock_item = MagicMock()
        mock_item.file_content = b"\xff\xd8\xff" + b"x" * 10
        mock_item.content_type = "image/jpeg"
        mock_item.filename = "img.jpg"

        tool, mock_media = self._get_tool(media_results=[mock_item, None])

        result = await tool.ainvoke(
            {"phone_number": "5511999", "queries": ["found desc", "not found desc"]}
        )

        mock_upload.assert_awaited_once()
        self.assertIn("Sent 1 media file(s) to 5511999", result)
        self.assertIn("Not found for:", result)
        self.assertIn("not found desc", result)

    @patch("delpro_backend.assistant.agent_tools.whatsapp_api.upload_media", new_callable=AsyncMock)
    async def test_sends_multiple_media(self, mock_upload):
        """Test that multiple matching media files are all sent."""
        mock_item1 = MagicMock()
        mock_item1.file_content = b"\xff\xd8\xff" + b"a" * 10
        mock_item1.content_type = "image/jpeg"
        mock_item1.filename = "a.jpg"

        mock_item2 = MagicMock()
        mock_item2.file_content = b"\xff\xd8\xff" + b"b" * 10
        mock_item2.content_type = "image/jpeg"
        mock_item2.filename = "b.jpg"

        tool, _ = self._get_tool(media_results=[mock_item1, mock_item2])

        result = await tool.ainvoke(
            {"phone_number": "5511999", "queries": ["desc1", "desc2"]}
        )

        self.assertEqual(mock_upload.await_count, 2)
        self.assertIn("Sent 2 media file(s) to 5511999", result)
