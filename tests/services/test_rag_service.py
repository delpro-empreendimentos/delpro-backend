"""Tests for RAGService."""

import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from delpro_backend.models.v1.exception_models import DocumentProcessingError
from delpro_backend.services.rag_service import RAGService
from tests.keys_test import DEFAULT_KEYS

for key, value in DEFAULT_KEYS.items():
    os.environ.setdefault(key, value)
os.environ.setdefault("MAX_TOKENS_SUMMARY", "500")


class TestRAGServiceRetrieveContext(unittest.IsolatedAsyncioTestCase):
    """Tests for RAGService.retrieve_context."""

    @patch("delpro_backend.services.rag_service.settings")
    async def test_retrieve_context_returns_empty_when_rag_disabled(self, mock_settings):
        """Test that retrieve_context returns empty when RAG is disabled."""
        mock_settings.ENABLE_RAG = False

        result = await RAGService.retrieve_context("test query")

        self.assertEqual(result["context"], "")
        self.assertEqual(result["sources"], [])
        self.assertEqual(result["chunk_count"], 0)

    @patch("delpro_backend.services.rag_service.VectorService")
    @patch("delpro_backend.services.rag_service.get_embeddings")
    @patch("delpro_backend.services.rag_service.settings")
    async def test_retrieve_context_generates_query_embedding(
        self, mock_settings, mock_get_embeddings, mock_vector_service
    ):
        """Test that query embedding is generated for the query."""
        mock_settings.ENABLE_RAG = True
        mock_settings.RAG_TOP_K = 1

        mock_embeddings_model = AsyncMock()
        mock_embeddings_model.aembed_query.return_value = [0.1] * 768
        mock_get_embeddings.return_value = mock_embeddings_model

        mock_vector_service.semantic_search = AsyncMock(return_value=[])

        await RAGService.retrieve_context("test query")

        mock_embeddings_model.aembed_query.assert_called_once_with("test query")

    @patch("delpro_backend.services.rag_service.VectorService")
    @patch("delpro_backend.services.rag_service.get_embeddings")
    @patch("delpro_backend.services.rag_service.settings")
    async def test_retrieve_context_calls_semantic_search(
        self, mock_settings, mock_get_embeddings, mock_vector_service
    ):
        """Test that semantic search is called with embedding and top_k."""
        mock_settings.ENABLE_RAG = True
        mock_settings.RAG_TOP_K = 3

        mock_embeddings_model = AsyncMock()
        query_embedding = [0.1] * 768
        mock_embeddings_model.aembed_query.return_value = query_embedding
        mock_get_embeddings.return_value = mock_embeddings_model

        mock_vector_service.semantic_search = AsyncMock(return_value=[])

        await RAGService.retrieve_context("test query", top_k=2)

        mock_vector_service.semantic_search.assert_called_once_with(query_embedding, top_k=2)

    @patch("delpro_backend.services.rag_service.VectorService")
    @patch("delpro_backend.services.rag_service.get_embeddings")
    @patch("delpro_backend.services.rag_service.settings")
    async def test_retrieve_context_returns_formatted_context(
        self, mock_settings, mock_get_embeddings, mock_vector_service
    ):
        """Test that context is formatted correctly from search results."""
        mock_settings.ENABLE_RAG = True
        mock_settings.RAG_TOP_K = 2

        mock_embeddings_model = AsyncMock()
        mock_embeddings_model.aembed_query.return_value = [0.1] * 768
        mock_get_embeddings.return_value = mock_embeddings_model

        # Mock chunk results
        mock_chunk1 = MagicMock()
        mock_chunk1.content = "First chunk about apartments"
        mock_chunk2 = MagicMock()
        mock_chunk2.content = "Second chunk about pricing"

        mock_vector_service.semantic_search = AsyncMock(
            return_value=[
                (mock_chunk1, 0.95),
                (mock_chunk2, 0.85),
            ]
        )

        result = await RAGService.retrieve_context("apartments")

        self.assertIn("First chunk about apartments", result["context"])
        self.assertIn("Second chunk about pricing", result["context"])
        self.assertIn("---", result["context"])  # Separator
        self.assertEqual(result["chunk_count"], 2)

    @patch("delpro_backend.services.rag_service.VectorService")
    @patch("delpro_backend.services.rag_service.get_embeddings")
    @patch("delpro_backend.services.rag_service.settings")
    async def test_retrieve_context_empty_results(
        self, mock_settings, mock_get_embeddings, mock_vector_service
    ):
        """Test that empty results return empty context."""
        mock_settings.ENABLE_RAG = True
        mock_settings.RAG_TOP_K = 1

        mock_embeddings_model = AsyncMock()
        mock_embeddings_model.aembed_query.return_value = [0.1] * 768
        mock_get_embeddings.return_value = mock_embeddings_model

        mock_vector_service.semantic_search = AsyncMock(return_value=[])

        result = await RAGService.retrieve_context("no matching docs")

        self.assertEqual(result["context"], "")
        self.assertEqual(result["sources"], [])
        self.assertEqual(result["chunk_count"], 0)

    @patch("delpro_backend.services.rag_service.VectorService")
    @patch("delpro_backend.services.rag_service.get_embeddings")
    @patch("delpro_backend.services.rag_service.settings")
    async def test_retrieve_context_uses_default_top_k(
        self, mock_settings, mock_get_embeddings, mock_vector_service
    ):
        """Test that default RAG_TOP_K from settings is used when not specified."""
        mock_settings.ENABLE_RAG = True
        mock_settings.RAG_TOP_K = 5

        mock_embeddings_model = AsyncMock()
        mock_embeddings_model.aembed_query.return_value = [0.1] * 768
        mock_get_embeddings.return_value = mock_embeddings_model

        mock_vector_service.semantic_search = AsyncMock(return_value=[])

        await RAGService.retrieve_context("query without top_k")

        mock_vector_service.semantic_search.assert_called_once()
        _, kwargs = mock_vector_service.semantic_search.call_args
        self.assertEqual(kwargs["top_k"], 5)


class TestRAGServiceExtractText(unittest.IsolatedAsyncioTestCase):
    """Tests for RAGService text extraction methods."""

    async def test_extract_text_from_txt(self):
        """Test extracting text from TXT file bytes."""
        content = "Hello, this is test content.\nWith multiple lines."
        file_bytes = content.encode("utf-8")

        result = await RAGService.extract_text_from_txt(file_bytes)

        self.assertEqual(result, content)

    async def test_extract_text_from_txt_handles_encoding_errors(self):
        """Test that invalid UTF-8 bytes are handled gracefully."""
        # Invalid UTF-8 sequence
        file_bytes = b"Valid text \xff\xfe invalid bytes"

        result = await RAGService.extract_text_from_txt(file_bytes)

        # Should not raise, uses errors='replace'
        self.assertIn("Valid text", result)

    @patch("delpro_backend.services.rag_service.PdfReader")
    async def test_extract_text_from_pdf(self, mock_pdf_reader):
        """Test extracting text from PDF file bytes."""
        # Mock PDF pages
        mock_page1 = MagicMock()
        mock_page1.extract_text.return_value = "Page 1 content"
        mock_page2 = MagicMock()
        mock_page2.extract_text.return_value = "Page 2 content"

        mock_reader_instance = MagicMock()
        mock_reader_instance.pages = [mock_page1, mock_page2]
        mock_pdf_reader.return_value = mock_reader_instance

        result = await RAGService.extract_text_from_pdf(b"fake pdf bytes")

        self.assertIn("Page 1 content", result)
        self.assertIn("Page 2 content", result)
        self.assertIn("\n\n", result)  # Pages separated by double newline


class TestRAGServiceChunkText(unittest.IsolatedAsyncioTestCase):
    """Tests for RAGService.chunk_text."""

    async def test_chunk_text_returns_chunks(self):
        """Test that chunk_text splits text into chunks."""
        text = "This is a test. " * 100  # Create text that will be chunked

        result = await RAGService.chunk_text(text)

        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)
        self.assertIn("content", result[0])
        self.assertIn("chunk_index", result[0])
        self.assertIn("metadata", result[0])

    async def test_chunk_text_preserves_content(self):
        """Test that all content is preserved across chunks."""
        text = "Short text that fits in one chunk."

        result = await RAGService.chunk_text(text)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["content"], text)
        self.assertEqual(result[0]["chunk_index"], 0)

    async def test_chunk_text_metadata_includes_char_count(self):
        """Test that metadata includes character count."""
        text = "Test content"

        result = await RAGService.chunk_text(text)

        self.assertEqual(result[0]["metadata"]["char_count"], len(text))
        self.assertEqual(result[0]["metadata"]["position"], 0)


class TestRAGServiceProcessDocument(unittest.IsolatedAsyncioTestCase):
    """Tests for RAGService.process_document."""

    @patch("delpro_backend.services.rag_service.DocumentService")
    @patch("delpro_backend.services.rag_service.VectorService")
    async def test_process_document_txt(self, mock_vector_service, mock_doc_service):
        """Test processing a TXT document."""
        mock_vector_service.save_chunks_with_embeddings = AsyncMock(return_value=2)
        mock_doc_service.update_document_status = AsyncMock()

        content = "Test document content. " * 50
        file_bytes = content.encode("utf-8")

        result = await RAGService.process_document("doc-123", file_bytes, "text/plain")

        self.assertEqual(result, 2)
        mock_vector_service.save_chunks_with_embeddings.assert_called_once()
        mock_doc_service.update_document_status.assert_called_with("doc-123", "completed")

    @patch("delpro_backend.services.rag_service.DocumentService")
    @patch("delpro_backend.services.rag_service.VectorService")
    @patch("delpro_backend.services.rag_service.PdfReader")
    async def test_process_document_pdf(
        self, mock_pdf_reader, mock_vector_service, mock_doc_service
    ):
        """Test processing a PDF document."""
        # Mock PDF reader
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "PDF content here. " * 50
        mock_reader_instance = MagicMock()
        mock_reader_instance.pages = [mock_page]
        mock_pdf_reader.return_value = mock_reader_instance

        mock_vector_service.save_chunks_with_embeddings = AsyncMock(return_value=1)
        mock_doc_service.update_document_status = AsyncMock()

        result = await RAGService.process_document("doc-pdf-123", b"fake pdf", "application/pdf")

        self.assertEqual(result, 1)
        mock_vector_service.save_chunks_with_embeddings.assert_called_once()
        mock_doc_service.update_document_status.assert_called_with("doc-pdf-123", "completed")

    @patch("delpro_backend.services.rag_service.DocumentService")
    @patch("delpro_backend.services.rag_service.VectorService")
    async def test_process_document_unsupported_type(self, mock_vector_service, mock_doc_service):
        """Test that unsupported content types raise DocumentProcessingError."""
        mock_doc_service.update_document_status = AsyncMock()

        with self.assertRaises(DocumentProcessingError):
            await RAGService.process_document("doc-123", b"content", "application/json")

        mock_doc_service.update_document_status.assert_called_with("doc-123", "failed")

    @patch("delpro_backend.services.rag_service.DocumentService")
    @patch("delpro_backend.services.rag_service.VectorService")
    async def test_process_document_updates_status_on_failure(
        self, mock_vector_service, mock_doc_service
    ):
        """Test that document status is set to 'failed' on error."""
        mock_vector_service.save_chunks_with_embeddings = AsyncMock(
            side_effect=Exception("Database error")
        )
        mock_doc_service.update_document_status = AsyncMock()

        with self.assertRaises(DocumentProcessingError):
            await RAGService.process_document("doc-123", b"content", "text/plain")

        mock_doc_service.update_document_status.assert_called_with("doc-123", "failed")
