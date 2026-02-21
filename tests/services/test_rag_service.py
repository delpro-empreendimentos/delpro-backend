"""Tests for RAGService."""

import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from delpro_backend.models.v1.exception_models import DocumentProcessingError
from delpro_backend.services.rag_service import RAGService
from delpro_backend.services.vector_service import VectorService
from tests.keys_test import DEFAULT_KEYS

for key, value in DEFAULT_KEYS.items():
    os.environ.setdefault(key, value)


def _make_rag_service(vector_result=None):
    """Create a RAGService with mocked dependencies."""
    mock_embeddings = AsyncMock()
    mock_embeddings.aembed_query = AsyncMock(return_value=[0.1] * 3072)

    mock_vector = MagicMock(spec=VectorService)
    mock_vector.semantic_search = AsyncMock(return_value=vector_result)

    svc = RAGService(vector_service=mock_vector, embeddings=mock_embeddings)
    return svc, mock_embeddings, mock_vector


class TestRAGServiceExtractText(unittest.TestCase):
    """Tests for RAGService text extraction methods."""

    def setUp(self):
        svc, _, _ = _make_rag_service()
        self.svc = svc

    def test_extract_text_from_txt(self):
        """Test extracting text from TXT file bytes."""
        content = "Hello, this is test content.\nWith multiple lines."
        result = self.svc._extract_text_from_txt(content.encode("utf-8"))
        self.assertEqual(result, content)

    def test_extract_text_from_txt_handles_encoding_errors(self):
        """Test that invalid UTF-8 bytes are handled gracefully."""
        file_bytes = b"Valid text \xff\xfe invalid bytes"
        result = self.svc._extract_text_from_txt(file_bytes)
        self.assertIn("Valid text", result)

    @patch("delpro_backend.services.rag_service.PdfReader")
    def test_extract_text_from_pdf(self, mock_pdf_reader):
        """Test extracting text from PDF file bytes."""
        mock_page1 = MagicMock()
        mock_page1.extract_text.return_value = "Page 1 content"
        mock_page2 = MagicMock()
        mock_page2.extract_text.return_value = "Page 2 content"

        mock_reader_instance = MagicMock()
        mock_reader_instance.pages = [mock_page1, mock_page2]
        mock_pdf_reader.return_value = mock_reader_instance

        result = self.svc._extract_text_from_pdf(b"fake pdf bytes")

        self.assertIn("Page 1 content", result)
        self.assertIn("Page 2 content", result)
        self.assertIn("\n\n", result)


class TestRAGServiceChunkText(unittest.TestCase):
    """Tests for RAGService._chunk_text."""

    def setUp(self):
        svc, _, _ = _make_rag_service()
        self.svc = svc

    def test_chunk_text_returns_chunks(self):
        """Test that chunk_text splits text into chunks."""
        text = "This is a test. " * 100
        result = self.svc._chunk_text(text)
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)
        self.assertIn("content", result[0])
        self.assertIn("chunk_index", result[0])
        self.assertIn("metadata", result[0])

    def test_chunk_text_preserves_content(self):
        """Test that all content is preserved in a single chunk."""
        text = "Short text that fits in one chunk."
        result = self.svc._chunk_text(text)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["content"], text)
        self.assertEqual(result[0]["chunk_index"], 0)

    def test_chunk_text_metadata_includes_char_count(self):
        """Test that metadata includes character count."""
        text = "Test content"
        result = self.svc._chunk_text(text)
        self.assertEqual(result[0]["metadata"]["char_count"], len(text))
        self.assertEqual(result[0]["metadata"]["position"], 0)


class TestRAGServiceProcessDocument(unittest.IsolatedAsyncioTestCase):
    """Tests for RAGService.process_document."""

    async def test_process_document_txt(self):
        """Test processing a TXT document."""
        svc, _, mock_vector = _make_rag_service()
        mock_vector.save_chunks_with_embeddings = AsyncMock(return_value=2)

        content = "Test document content. " * 50
        result = await svc.process_document("doc-123", content.encode("utf-8"), "text/plain")

        self.assertEqual(result, 2)
        mock_vector.save_chunks_with_embeddings.assert_awaited_once()

    async def test_process_document_pdf(self):
        """Test processing a PDF document."""
        svc, _, mock_vector = _make_rag_service()
        mock_vector.save_chunks_with_embeddings = AsyncMock(return_value=1)

        with patch("delpro_backend.services.rag_service.PdfReader") as mock_pdf_reader:
            mock_page = MagicMock()
            mock_page.extract_text.return_value = "PDF content. " * 50
            mock_reader_instance = MagicMock()
            mock_reader_instance.pages = [mock_page]
            mock_pdf_reader.return_value = mock_reader_instance

            result = await svc.process_document("doc-pdf-123", b"fake pdf", "application/pdf")

        self.assertEqual(result, 1)
        mock_vector.save_chunks_with_embeddings.assert_awaited_once()

    async def test_process_document_unsupported_type_raises(self):
        """Test that unsupported content types raise DocumentProcessingError."""
        svc, _, _ = _make_rag_service()

        with self.assertRaises(DocumentProcessingError):
            await svc.process_document("doc-123", b"content", "application/json")

    async def test_process_document_vector_error_raises(self):
        """Test that vector service failure raises DocumentProcessingError."""
        svc, _, mock_vector = _make_rag_service()
        mock_vector.save_chunks_with_embeddings = AsyncMock(side_effect=RuntimeError("DB down"))

        content = "Test content. " * 50
        with self.assertRaises(DocumentProcessingError):
            await svc.process_document("doc-123", content.encode(), "text/plain")


class TestRAGServiceRetrieveContext(unittest.IsolatedAsyncioTestCase):
    """Tests for RAGService.retrieve_context."""

    async def test_retrieve_context_generates_embedding_and_calls_search(self):
        """Test that query embedding is generated and semantic search called."""
        svc, mock_embeddings, mock_vector = _make_rag_service(vector_result="Found content")

        result = await svc.retrieve_context("test query")

        mock_embeddings.aembed_query.assert_awaited_once_with("test query")
        mock_vector.semantic_search.assert_awaited_once()
        self.assertEqual(result, "Found content")

    async def test_retrieve_context_returns_none_when_empty(self):
        """Test that None is returned when no chunks found."""
        svc, _, mock_vector = _make_rag_service(vector_result=None)

        result = await svc.retrieve_context("no match query")

        self.assertIsNone(result)
