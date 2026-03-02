"""Tests for DocumentService."""

import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from tests.keys_test import DEFAULT_KEYS

for key, value in DEFAULT_KEYS.items():
    os.environ.setdefault(key, value)

from delpro_backend.models.v1.database_models import DocumentRow  # noqa: E402
from delpro_backend.models.v1.document_models import UpdateDocumentMetadataRequest  # noqa: E402
from delpro_backend.models.v1.exception_models import (  # noqa: E402
    InvalidRequestError,
    ResourceNotFoundError,
)
from delpro_backend.services.document_service import DocumentService  # noqa: E402

PATCH_DB = "delpro_backend.services.document_service.AsyncSessionFactory"


def _make_service(rag_result=0):
    mock_rag = MagicMock()
    mock_rag.process_document = AsyncMock(return_value=rag_result)
    return DocumentService(rag_service=mock_rag), mock_rag


class TestGetDocumentContent(unittest.IsolatedAsyncioTestCase):
    """Tests for DocumentService.get_document_content."""

    @patch(PATCH_DB)
    async def test_returns_bytes_content_type_filename(self, mock_factory):
        """Test get_document_content returns (bytes, content_type, filename)."""
        svc, _ = _make_service()

        mock_doc = MagicMock(spec=DocumentRow)
        mock_doc.file_content = b"hello"
        mock_doc.content_type = "text/plain"
        mock_doc.filename = "doc.txt"

        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=mock_doc)
        mock_factory.return_value.__aenter__.return_value = mock_session

        content, ctype, fname = await svc.get_document_content("doc-123")

        self.assertEqual(content, b"hello")
        self.assertEqual(ctype, "text/plain")
        self.assertEqual(fname, "doc.txt")

    @patch(PATCH_DB)
    async def test_raises_when_not_found(self, mock_factory):
        """Test that ResourceNotFoundError is raised when document not found."""
        svc, _ = _make_service()

        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=None)
        mock_factory.return_value.__aenter__.return_value = mock_session

        with self.assertRaises(ResourceNotFoundError):
            await svc.get_document_content("nonexistent")


class TestUpdateDocumentContent(unittest.IsolatedAsyncioTestCase):
    """Tests for DocumentService.update_document_content."""

    @patch(PATCH_DB)
    async def test_updates_text_document_successfully(self, mock_factory):
        """Test updating a text/plain document re-processes it."""
        svc, mock_rag = _make_service(rag_result=3)

        mock_doc = MagicMock(spec=DocumentRow)
        mock_doc.content_type = "text/plain"
        mock_doc.id = "doc-123"

        mock_chunk_result = MagicMock()
        mock_chunk_result.scalars.return_value.all.return_value = []

        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=mock_doc)
        mock_session.execute = AsyncMock(return_value=mock_chunk_result)
        mock_session.refresh = AsyncMock(return_value=None)
        mock_factory.return_value.__aenter__.return_value = mock_session

        # update_document_status also uses AsyncSessionFactory
        with patch.object(svc, "update_document_status", new_callable=AsyncMock):
            result = await svc.update_document_content("doc-123", b"new content")

        mock_rag.process_document.assert_awaited_once_with("doc-123", b"new content", "text/plain")
        self.assertEqual(result, mock_doc)

    @patch(PATCH_DB)
    async def test_raises_when_not_found(self, mock_factory):
        """Test that ResourceNotFoundError is raised when document not found."""
        svc, _ = _make_service()

        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=None)
        mock_factory.return_value.__aenter__.return_value = mock_session

        with self.assertRaises(ResourceNotFoundError):
            await svc.update_document_content("nonexistent", b"content")

    @patch(PATCH_DB)
    async def test_raises_for_non_text_document(self, mock_factory):
        """Test that InvalidRequestError is raised for non-text documents."""
        svc, _ = _make_service()

        mock_doc = MagicMock(spec=DocumentRow)
        mock_doc.content_type = "application/pdf"

        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=mock_doc)
        mock_factory.return_value.__aenter__.return_value = mock_session

        with self.assertRaises(InvalidRequestError):
            await svc.update_document_content("doc-123", b"content")


class TestUpdateDocumentMetadata(unittest.IsolatedAsyncioTestCase):
    """Tests for DocumentService.update_document_metadata."""

    @patch(PATCH_DB)
    async def test_updates_filename_successfully(self, mock_factory):
        """Test updating the filename of a document."""
        svc, _ = _make_service()

        mock_doc = MagicMock(spec=DocumentRow)
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=mock_doc)
        mock_session.refresh = AsyncMock(return_value=None)
        mock_factory.return_value.__aenter__.return_value = mock_session

        data = UpdateDocumentMetadataRequest(filename="new_name.txt")
        result = await svc.update_document_metadata("doc-123", data)

        self.assertEqual(mock_doc.filename, "new_name.txt")
        self.assertEqual(result, mock_doc)

    @patch(PATCH_DB)
    async def test_skips_filename_update_when_none(self, mock_factory):
        """Test that filename is not updated when data.filename is None."""
        svc, _ = _make_service()

        mock_doc = MagicMock(spec=DocumentRow)
        mock_doc.filename = "original.txt"
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=mock_doc)
        mock_session.refresh = AsyncMock(return_value=None)
        mock_factory.return_value.__aenter__.return_value = mock_session

        data = UpdateDocumentMetadataRequest()
        result = await svc.update_document_metadata("doc-123", data)

        self.assertEqual(mock_doc.filename, "original.txt")

    @patch(PATCH_DB)
    async def test_raises_when_not_found(self, mock_factory):
        """Test that ResourceNotFoundError is raised when document not found."""
        svc, _ = _make_service()

        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=None)
        mock_factory.return_value.__aenter__.return_value = mock_session

        data = UpdateDocumentMetadataRequest(filename="x.txt")
        with self.assertRaises(ResourceNotFoundError):
            await svc.update_document_metadata("nonexistent", data)


class TestUpdateDocumentContentWithChunks(unittest.IsolatedAsyncioTestCase):
    """Tests for DocumentService.update_document_content with existing chunks to delete."""

    @patch(PATCH_DB)
    async def test_deletes_existing_chunks_before_reprocessing(self, mock_factory):
        """Test that existing chunks are deleted when updating document content."""
        svc, mock_rag = _make_service(rag_result=2)

        mock_doc = MagicMock(spec=DocumentRow)
        mock_doc.content_type = "text/plain"
        mock_doc.id = "doc-123"

        # Simulate existing chunks
        mock_chunk1 = MagicMock()
        mock_chunk2 = MagicMock()
        mock_chunk_result = MagicMock()
        mock_chunk_result.scalars.return_value.all.return_value = [mock_chunk1, mock_chunk2]

        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=mock_doc)
        mock_session.execute = AsyncMock(return_value=mock_chunk_result)
        mock_session.refresh = AsyncMock(return_value=None)
        mock_factory.return_value.__aenter__.return_value = mock_session

        with patch.object(svc, "update_document_status", new_callable=AsyncMock):
            await svc.update_document_content("doc-123", b"new content")

        # Both chunks should have been deleted
        self.assertEqual(mock_session.delete.await_count, 2)
        mock_session.delete.assert_any_await(mock_chunk1)
        mock_session.delete.assert_any_await(mock_chunk2)
