"""Tests for DocumentService."""

import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from delpro_backend.models.v1.exception_models import ResourceNotFoundError
from delpro_backend.models.v1.database_models import ChunkRow, DocumentRow
from tests.keys_test import DEFAULT_KEYS

for key, value in DEFAULT_KEYS.items():
    os.environ.setdefault(key, value)


def _make_service():
    """Create a DocumentService with a mocked RAGService."""
    from delpro_backend.services.document_service import DocumentService

    mock_rag = MagicMock()
    mock_rag.process_document = AsyncMock(return_value=5)
    return DocumentService(rag_service=mock_rag), mock_rag


class TestDocumentServiceCreateDocument(unittest.IsolatedAsyncioTestCase):
    """Tests for DocumentService.create_document."""

    @patch("delpro_backend.services.document_service.AsyncSessionFactory")
    async def test_creates_document_with_correct_fields(self, mock_factory):
        """Test that create_document creates a document with correct fields."""
        svc, mock_rag = _make_service()

        mock_session = AsyncMock()
        mock_session.add = MagicMock()

        captured = {}

        def capture_add(doc):
            captured["doc"] = doc

        mock_session.add = capture_add
        mock_factory.return_value.__aenter__.return_value = mock_session

        mock_file = MagicMock()
        mock_file.content_type = "text/plain"
        mock_file.filename = "test.txt"
        mock_file.read = AsyncMock(return_value=b"hello world")

        result = await svc.create_document(files=[mock_file])

        self.assertEqual(len(result), 1)
        self.assertEqual(captured["doc"].file_size_bytes, 11)
        self.assertEqual(captured["doc"].status, "processing")

    @patch("delpro_backend.services.document_service.AsyncSessionFactory")
    async def test_raises_when_no_files(self, mock_factory):
        """Test that MissingParametersRequestError is raised with no files."""
        from delpro_backend.models.v1.exception_models import MissingParametersRequestError

        svc, _ = _make_service()
        with self.assertRaises(MissingParametersRequestError):
            await svc.create_document(files=[])

    @patch("delpro_backend.services.document_service.AsyncSessionFactory")
    async def test_raises_when_too_many_files(self, mock_factory):
        """Test that InvalidRequestError is raised when too many files."""
        from delpro_backend.models.v1.exception_models import InvalidRequestError
        from delpro_backend.utils.settings import settings

        svc, _ = _make_service()

        files = [MagicMock(content_type="text/plain") for _ in range(settings.MAX_FILES_PER_UPLOAD + 1)]
        with self.assertRaises(InvalidRequestError):
            await svc.create_document(files=files)

    @patch("delpro_backend.services.document_service.AsyncSessionFactory")
    async def test_raises_on_invalid_content_type(self, mock_factory):
        """Test that InvalidRequestError is raised for unsupported file types."""
        from delpro_backend.models.v1.exception_models import InvalidRequestError

        svc, _ = _make_service()

        mock_file = MagicMock()
        mock_file.content_type = "image/png"

        with self.assertRaises(InvalidRequestError):
            await svc.create_document(files=[mock_file])

    @patch("delpro_backend.services.document_service.AsyncSessionFactory")
    async def test_raises_on_oversized_file(self, mock_factory):
        """Test that InvalidRequestError is raised when file is too large."""
        from delpro_backend.models.v1.exception_models import InvalidRequestError
        from delpro_backend.utils.settings import settings

        svc, _ = _make_service()
        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_factory.return_value.__aenter__.return_value = mock_session

        big_bytes = b"x" * int(settings.MAX_FILE_SIZE_MB * 1024 * 1024 + 1)

        mock_file = MagicMock()
        mock_file.content_type = "text/plain"
        mock_file.filename = "big.txt"
        mock_file.read = AsyncMock(return_value=big_bytes)

        with self.assertRaises(InvalidRequestError):
            await svc.create_document(files=[mock_file])


class TestDocumentServiceUpdateStatus(unittest.IsolatedAsyncioTestCase):
    """Tests for DocumentService.update_document_status."""

    @patch("delpro_backend.services.document_service.AsyncSessionFactory")
    async def test_updates_status_when_document_exists(self, mock_factory):
        """Test that status is updated when document exists."""
        svc, _ = _make_service()

        mock_doc = MagicMock(spec=DocumentRow)
        mock_doc.status = "processing"

        mock_session = AsyncMock()
        mock_session.get.return_value = mock_doc
        mock_factory.return_value.__aenter__.return_value = mock_session

        await svc.update_document_status("doc-123", "completed")

        self.assertEqual(mock_doc.status, "completed")
        mock_session.commit.assert_awaited_once()

    @patch("delpro_backend.services.document_service.AsyncSessionFactory")
    async def test_raises_not_found_when_document_missing(self, mock_factory):
        """Test that ResourceNotFoundError is raised when document not found."""
        svc, _ = _make_service()

        mock_session = AsyncMock()
        mock_session.get.return_value = None
        mock_factory.return_value.__aenter__.return_value = mock_session

        with self.assertRaises(ResourceNotFoundError) as cm:
            await svc.update_document_status("missing-doc", "completed")

        self.assertEqual(cm.exception.resource_type, "Document")
        self.assertEqual(cm.exception.resource_id, "missing-doc")


class TestDocumentServiceGetDocument(unittest.IsolatedAsyncioTestCase):
    """Tests for DocumentService.get_document."""

    @patch("delpro_backend.services.document_service.AsyncSessionFactory")
    async def test_returns_document_when_exists(self, mock_factory):
        """Test that document is returned when it exists."""
        svc, _ = _make_service()

        mock_doc = MagicMock(spec=DocumentRow)
        mock_doc.id = "doc-123"
        mock_doc.filename = "test.pdf"

        mock_session = AsyncMock()
        mock_session.get.return_value = mock_doc
        mock_factory.return_value.__aenter__.return_value = mock_session

        result = await svc.get_document("doc-123")

        self.assertEqual(result.id, "doc-123")
        self.assertEqual(result.filename, "test.pdf")

    @patch("delpro_backend.services.document_service.AsyncSessionFactory")
    async def test_raises_not_found_when_missing(self, mock_factory):
        """Test that ResourceNotFoundError is raised when document not found."""
        svc, _ = _make_service()

        mock_session = AsyncMock()
        mock_session.get.return_value = None
        mock_factory.return_value.__aenter__.return_value = mock_session

        with self.assertRaises(ResourceNotFoundError):
            await svc.get_document("nonexistent")


class TestDocumentServiceListDocuments(unittest.IsolatedAsyncioTestCase):
    """Tests for DocumentService.list_documents."""

    @patch("delpro_backend.services.document_service.AsyncSessionFactory")
    async def test_returns_documents_with_chunk_counts(self, mock_factory):
        """Test that list_documents returns documents with chunk counts and total."""
        svc, _ = _make_service()

        mock_doc1 = MagicMock(spec=DocumentRow)
        mock_doc1.id = "doc-1"
        mock_doc2 = MagicMock(spec=DocumentRow)
        mock_doc2.id = "doc-2"

        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 2
        mock_data_result = MagicMock()
        mock_data_result.all.return_value = [(mock_doc1, 5), (mock_doc2, 3)]

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=[mock_count_result, mock_data_result])
        mock_factory.return_value.__aenter__.return_value = mock_session

        rows, total = await svc.list_documents()

        self.assertEqual(len(rows), 2)
        self.assertEqual(total, 2)
        self.assertEqual(rows[0][0].id, "doc-1")
        self.assertEqual(rows[0][1], 5)
        self.assertEqual(rows[1][0].id, "doc-2")
        self.assertEqual(rows[1][1], 3)

    @patch("delpro_backend.services.document_service.AsyncSessionFactory")
    async def test_returns_empty_list_when_no_documents(self, mock_factory):
        """Test that empty list is returned when no documents."""
        svc, _ = _make_service()

        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 0
        mock_data_result = MagicMock()
        mock_data_result.all.return_value = []

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=[mock_count_result, mock_data_result])
        mock_factory.return_value.__aenter__.return_value = mock_session

        rows, total = await svc.list_documents()

        self.assertEqual(rows, [])
        self.assertEqual(total, 0)

    @patch("delpro_backend.services.document_service.AsyncSessionFactory")
    async def test_reraises_on_exception(self, mock_factory):
        """Test that exceptions from the DB are propagated."""
        svc, _ = _make_service()

        mock_session = AsyncMock()
        mock_session.execute.side_effect = RuntimeError("DB error")
        mock_factory.return_value.__aenter__.return_value = mock_session

        with self.assertRaises(RuntimeError):
            await svc.list_documents()


class TestDocumentServiceGetDocumentWithChunks(unittest.IsolatedAsyncioTestCase):
    """Tests for DocumentService.get_document_with_chunks."""

    @patch("delpro_backend.services.document_service.AsyncSessionFactory")
    async def test_returns_document_and_chunks(self, mock_factory):
        """Test that document and chunks are returned together."""
        svc, _ = _make_service()

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

        doc, chunks = await svc.get_document_with_chunks("doc-123")

        self.assertEqual(doc.id, "doc-123")
        self.assertEqual(len(chunks), 2)

    @patch("delpro_backend.services.document_service.AsyncSessionFactory")
    async def test_raises_not_found_when_document_missing(self, mock_factory):
        """Test that ResourceNotFoundError is raised when document not found."""
        svc, _ = _make_service()

        mock_session = AsyncMock()
        mock_session.get.return_value = None
        mock_factory.return_value.__aenter__.return_value = mock_session

        with self.assertRaises(ResourceNotFoundError):
            await svc.get_document_with_chunks("missing")


class TestDocumentServiceDeleteDocument(unittest.IsolatedAsyncioTestCase):
    """Tests for DocumentService.delete_document."""

    @patch("delpro_backend.services.document_service.AsyncSessionFactory")
    async def test_deletes_document_when_exists(self, mock_factory):
        """Test that document is deleted when it exists."""
        svc, _ = _make_service()

        mock_doc = MagicMock(spec=DocumentRow)
        mock_doc.id = "doc-to-delete"

        mock_session = AsyncMock()
        mock_session.get.return_value = mock_doc
        mock_factory.return_value.__aenter__.return_value = mock_session

        await svc.delete_document("doc-to-delete")

        mock_session.delete.assert_awaited_once_with(mock_doc)
        mock_session.commit.assert_awaited_once()

    @patch("delpro_backend.services.document_service.AsyncSessionFactory")
    async def test_raises_not_found_when_document_missing(self, mock_factory):
        """Test that ResourceNotFoundError is raised when document not found."""
        svc, _ = _make_service()

        mock_session = AsyncMock()
        mock_session.get.return_value = None
        mock_factory.return_value.__aenter__.return_value = mock_session

        with self.assertRaises(ResourceNotFoundError):
            await svc.delete_document("nonexistent")
