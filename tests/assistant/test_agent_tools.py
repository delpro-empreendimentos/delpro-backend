"""Tests for agent_tools.build_tools."""

import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from tests.keys_test import DEFAULT_KEYS

for key, value in DEFAULT_KEYS.items():
    os.environ.setdefault(key, value)

from delpro_backend.assistant.agent_tools import build_tools  # noqa: E402


def _make_services(rag_result=None, image_result=None):
    """Create mock RAGService and ImageService."""
    mock_rag = MagicMock()
    mock_rag.retrieve_context = AsyncMock(return_value=rag_result)

    mock_image = MagicMock()
    mock_image.search_image_by_description = AsyncMock(return_value=image_result)

    return mock_rag, mock_image


class TestBuildTools(unittest.TestCase):
    """Tests for build_tools factory."""

    def test_returns_two_tools(self):
        """Test that build_tools returns exactly two tools."""
        mock_rag, mock_image = _make_services()
        tools = build_tools(mock_rag, mock_image)
        self.assertEqual(len(tools), 2)

    def test_tool_names(self):
        """Test that both tools have the expected names."""
        mock_rag, mock_image = _make_services()
        tools = build_tools(mock_rag, mock_image)
        names = {t.name for t in tools}
        self.assertIn("search_knowledge_base", names)
        self.assertIn("send_whatsapp_image", names)


class TestSearchKnowledgeBase(unittest.IsolatedAsyncioTestCase):
    """Tests for search_knowledge_base tool."""

    def _get_tool(self, rag_result=None):
        mock_rag, mock_image = _make_services(rag_result=rag_result)
        tools = build_tools(mock_rag, mock_image)
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


class TestSendWhatsappImage(unittest.IsolatedAsyncioTestCase):
    """Tests for send_whatsapp_image tool."""

    def _get_tool(self, image_results=None):
        mock_rag, mock_image = _make_services()
        if image_results is not None:
            mock_image.search_image_by_description = AsyncMock(side_effect=image_results)
        tools = build_tools(mock_rag, mock_image)
        tool = next(t for t in tools if t.name == "send_whatsapp_image")
        return tool, mock_image

    @patch("delpro_backend.assistant.agent_tools.upload_media", new_callable=AsyncMock)
    async def test_sends_image_when_found(self, mock_upload):
        """Test that found images are uploaded and sent."""
        mock_img = MagicMock()
        mock_img.file_content = b"\xff\xd8\xff" + b"x" * 100
        mock_img.content_type = "image/jpeg"
        mock_img.filename = "photo.jpg"

        tool, mock_image = self._get_tool(image_results=[mock_img])

        result = await tool.ainvoke({"phone_number": "5511999", "descriptions": ["pool photo"]})

        mock_upload.assert_awaited_once_with(
            mock_img.file_content,
            mock_img.content_type,
            mock_img.filename,
            phone_number="5511999",
        )
        self.assertIn("Sent 1 image(s) to 5511999", result)

    @patch("delpro_backend.assistant.agent_tools.upload_media", new_callable=AsyncMock)
    async def test_returns_not_found_when_all_missing(self, mock_upload):
        """Test that message is returned when no images match."""
        tool, mock_image = self._get_tool(image_results=[None])

        result = await tool.ainvoke({"phone_number": "5511999", "descriptions": ["nothing"]})

        mock_upload.assert_not_awaited()
        self.assertIn("No matching images found", result)

    @patch("delpro_backend.assistant.agent_tools.upload_media", new_callable=AsyncMock)
    async def test_partial_match_reports_not_found(self, mock_upload):
        """Test that partial matches report which descriptions had no image."""
        mock_img = MagicMock()
        mock_img.file_content = b"\xff\xd8\xff" + b"x" * 10
        mock_img.content_type = "image/jpeg"
        mock_img.filename = "img.jpg"

        tool, mock_image = self._get_tool(image_results=[mock_img, None])

        result = await tool.ainvoke(
            {"phone_number": "5511999", "descriptions": ["found desc", "not found desc"]}
        )

        mock_upload.assert_awaited_once()
        self.assertIn("Sent 1 image(s) to 5511999", result)
        self.assertIn("Not found for:", result)
        self.assertIn("not found desc", result)

    @patch("delpro_backend.assistant.agent_tools.upload_media", new_callable=AsyncMock)
    async def test_sends_multiple_images(self, mock_upload):
        """Test that multiple matching images are all sent."""
        mock_img1 = MagicMock()
        mock_img1.file_content = b"\xff\xd8\xff" + b"a" * 10
        mock_img1.content_type = "image/jpeg"
        mock_img1.filename = "a.jpg"

        mock_img2 = MagicMock()
        mock_img2.file_content = b"\xff\xd8\xff" + b"b" * 10
        mock_img2.content_type = "image/jpeg"
        mock_img2.filename = "b.jpg"

        tool, _ = self._get_tool(image_results=[mock_img1, mock_img2])

        result = await tool.ainvoke(
            {"phone_number": "5511999", "descriptions": ["desc1", "desc2"]}
        )

        self.assertEqual(mock_upload.await_count, 2)
        self.assertIn("Sent 2 image(s) to 5511999", result)
