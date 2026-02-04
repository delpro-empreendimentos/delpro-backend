"""Tests for DocumentService."""

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
os.environ.setdefault("MAX_TOKENS_SUMMARY", "500")

from delpro_backend.db.document_service import DocumentService
from delpro_backend.db.exceptions import ResourceNotFoundError
from delpro_backend.db.models import ChunkRow, DocumentRow


class TestDocumentServiceCreateDocument(unittest.IsolatedAsyncioTestCase):
    """Tests for DocumentService.create_document."""

    @patch("delpro_backend.db.document_service.AsyncSessionFactory")
    async def test_creates_document_with_correct_fields(self, mock_factory):
        """Test that create_document creates a document with correct fields."""
        mock_session = AsyncMock()
        mock_session.add = MagicMock()

        # Mock the document after refresh
        created_doc = MagicMock(spec=DocumentRow)
        created_doc.id = "test-id"
        created_doc.filename = "test.txt"
        created_doc.content_type = "text/plain"
        created_doc.file_size_bytes = 100
        created_doc.status = "processing"

        async def mock_refresh(doc):
            doc.id = "test-id"
            doc.filename = "test.txt"
            doc.content_type = "text/plain"
            doc.file_size_bytes = 100
            doc.status = "processing"

        mock_session.refresh = mock_refresh
        mock_factory.return_value.__aenter__.return_value = mock_session

        result = await DocumentService.create_document(
            filename="test.txt",
            content_type="text/plain",
            file_bytes=b"x" * 100,
        )

        mock_session.add.assert_called_once()
        mock_session.commit.assert_awaited_once()

    @patch("delpro_backend.db.document_service.AsyncSessionFactory")
    async def test_creates_document_with_correct_size(self, mock_factory):
        """Test that file_size_bytes is calculated correctly."""
        mock_session = AsyncMock()
        mock_session.add = MagicMock()

        captured_doc = None

        def capture_add(doc):
            nonlocal captured_doc
            captured_doc = doc

        mock_session.add = capture_add
        mock_factory.return_value.__aenter__.return_value = mock_session

        await DocumentService.create_document(
            filename="test.txt",
            content_type="text/plain",
            file_bytes=b"hello world",  # 11 bytes
        )

        self.assertEqual(captured_doc.file_size_bytes, 11)
        self.assertEqual(captured_doc.status, "processing")


class TestDocumentServiceUpdateStatus(unittest.IsolatedAsyncioTestCase):
    """Tests for DocumentService.update_document_status."""

    @patch("delpro_backend.db.document_service.AsyncSessionFactory")
    async def test_updates_status_when_document_exists(self, mock_factory):
        """Test that status is updated when document exists."""
        mock_doc = MagicMock(spec=DocumentRow)
        mock_doc.status = "processing"

        mock_session = AsyncMock()
        mock_session.get.return_value = mock_doc
        mock_factory.return_value.__aenter__.return_value = mock_session

        await DocumentService.update_document_status("doc-123", "completed")

        self.assertEqual(mock_doc.status, "completed")
        mock_session.commit.assert_awaited_once()

    @patch("delpro_backend.db.document_service.AsyncSessionFactory")
    async def test_raises_not_found_when_document_missing(self, mock_factory):
        """Test that ResourceNotFoundError is raised when document not found."""
        mock_session = AsyncMock()
        mock_session.get.return_value = None
        mock_factory.return_value.__aenter__.return_value = mock_session

        with self.assertRaises(ResourceNotFoundError) as cm:
            await DocumentService.update_document_status("missing-doc", "completed")

        self.assertEqual(cm.exception.resource_type, "Document")
        self.assertEqual(cm.exception.resource_id, "missing-doc")


class TestDocumentServiceGetDocument(unittest.IsolatedAsyncioTestCase):
    """Tests for DocumentService.get_document."""

    @patch("delpro_backend.db.document_service.AsyncSessionFactory")
    async def test_returns_document_when_exists(self, mock_factory):
        """Test that document is returned when it exists."""
        mock_doc = MagicMock(spec=DocumentRow)
        mock_doc.id = "doc-123"
        mock_doc.filename = "test.pdf"

        mock_session = AsyncMock()
        mock_session.get.return_value = mock_doc
        mock_factory.return_value.__aenter__.return_value = mock_session

        result = await DocumentService.get_document("doc-123")

        self.assertEqual(result.id, "doc-123")
        self.assertEqual(result.filename, "test.pdf")

    @patch("delpro_backend.db.document_service.AsyncSessionFactory")
    async def test_raises_not_found_when_missing(self, mock_factory):
        """Test that ResourceNotFoundError is raised when document not found."""
        mock_session = AsyncMock()
        mock_session.get.return_value = None
        mock_factory.return_value.__aenter__.return_value = mock_session

        with self.assertRaises(ResourceNotFoundError):
            await DocumentService.get_document("nonexistent")


class TestDocumentServiceListDocuments(unittest.IsolatedAsyncioTestCase):
    """Tests for DocumentService.list_documents."""

    @patch("delpro_backend.db.document_service.AsyncSessionFactory")
    async def test_returns_documents_with_chunk_counts(self, mock_factory):
        """Test that list_documents returns documents with chunk counts."""
        mock_doc1 = MagicMock(spec=DocumentRow)
        mock_doc1.id = "doc-1"
        mock_doc2 = MagicMock(spec=DocumentRow)
        mock_doc2.id = "doc-2"

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = [
            (mock_doc1, 5),  # 5 chunks
            (mock_doc2, 3),  # 3 chunks
        ]
        mock_session.execute.return_value = mock_result
        mock_factory.return_value.__aenter__.return_value = mock_session

        result = await DocumentService.list_documents()

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0][0].id, "doc-1")
        self.assertEqual(result[0][1], 5)
        self.assertEqual(result[1][0].id, "doc-2")
        self.assertEqual(result[1][1], 3)

    @patch("delpro_backend.db.document_service.AsyncSessionFactory")
    async def test_returns_empty_list_when_no_documents(self, mock_factory):
        """Test that empty list is returned when no documents."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute.return_value = mock_result
        mock_factory.return_value.__aenter__.return_value = mock_session

        result = await DocumentService.list_documents()

        self.assertEqual(result, [])


class TestDocumentServiceGetDocumentWithChunks(unittest.IsolatedAsyncioTestCase):
    """Tests for DocumentService.get_document_with_chunks."""

    @patch("delpro_backend.db.document_service.AsyncSessionFactory")
    async def test_returns_document_and_chunks(self, mock_factory):
        """Test that document and chunks are returned together."""
        mock_doc = MagicMock(spec=DocumentRow)
        mock_doc.id = "doc-123"

        mock_chunk1 = MagicMock(spec=ChunkRow)
        mock_chunk1.chunk_index = 0
        mock_chunk2 = MagicMock(spec=ChunkRow)
        mock_chunk2.chunk_index = 1

        mock_session = AsyncMock()
        mock_session.get.return_value = mock_doc

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_chunk1, mock_chunk2]
        mock_session.execute.return_value = mock_result

        mock_factory.return_value.__aenter__.return_value = mock_session

        doc, chunks = await DocumentService.get_document_with_chunks("doc-123")

        self.assertEqual(doc.id, "doc-123")
        self.assertEqual(len(chunks), 2)

    @patch("delpro_backend.db.document_service.AsyncSessionFactory")
    async def test_raises_not_found_when_document_missing(self, mock_factory):
        """Test that ResourceNotFoundError is raised when document not found."""
        mock_session = AsyncMock()
        mock_session.get.return_value = None
        mock_factory.return_value.__aenter__.return_value = mock_session

        with self.assertRaises(ResourceNotFoundError):
            await DocumentService.get_document_with_chunks("missing")


class TestDocumentServiceDeleteDocument(unittest.IsolatedAsyncioTestCase):
    """Tests for DocumentService.delete_document."""

    @patch("delpro_backend.db.document_service.AsyncSessionFactory")
    async def test_deletes_document_when_exists(self, mock_factory):
        """Test that document is deleted when it exists."""
        mock_doc = MagicMock(spec=DocumentRow)
        mock_doc.id = "doc-to-delete"

        mock_session = AsyncMock()
        mock_session.get.return_value = mock_doc
        mock_factory.return_value.__aenter__.return_value = mock_session

        await DocumentService.delete_document("doc-to-delete")

        mock_session.delete.assert_awaited_once_with(mock_doc)
        mock_session.commit.assert_awaited_once()

    @patch("delpro_backend.db.document_service.AsyncSessionFactory")
    async def test_raises_not_found_when_document_missing(self, mock_factory):
        """Test that ResourceNotFoundError is raised when document not found."""
        mock_session = AsyncMock()
        mock_session.get.return_value = None
        mock_factory.return_value.__aenter__.return_value = mock_session

        with self.assertRaises(ResourceNotFoundError):
            await DocumentService.delete_document("nonexistent")
