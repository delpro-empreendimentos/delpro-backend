"""Tests for documents_router."""

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

from fastapi import HTTPException, UploadFile

from delpro_backend.db.exceptions import ResourceNotFoundError
from delpro_backend.db.models import ChunkRow, DocumentRow
from delpro_backend.routes.v1.documents_router import (
    delete_document,
    get_document,
    list_documents,
    test_endpoint,
    upload_documents,
)


class TestDocumentsRouterTestEndpoint(unittest.IsolatedAsyncioTestCase):
    """Tests for the test endpoint."""

    async def test_test_endpoint_returns_message(self):
        """Test that test endpoint returns success message."""
        result = await test_endpoint()
        self.assertIn("Documents router is working", result["message"])


class TestDocumentsRouterUpload(unittest.IsolatedAsyncioTestCase):
    """Tests for upload_documents endpoint."""

    @patch("delpro_backend.routes.v1.documents_router.RAGService")
    @patch("delpro_backend.routes.v1.documents_router.DocumentService")
    async def test_upload_documents_success(self, mock_doc_service, mock_rag_service):
        """Test successful document upload."""
        # Mock document creation
        mock_doc = MagicMock(spec=DocumentRow)
        mock_doc.id = "doc-123"
        mock_doc.filename = "test.txt"
        mock_doc.file_size_bytes = 12
        mock_doc_service.create_document = AsyncMock(return_value=mock_doc)

        # Mock processing
        mock_rag_service.process_document = AsyncMock(return_value=5)

        # Create mock file
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "test.txt"
        mock_file.content_type = "text/plain"
        mock_file.read = AsyncMock(return_value=b"test content")

        result = await upload_documents(files=[mock_file])

        self.assertEqual(result.status_code, 201)
        mock_doc_service.create_document.assert_awaited_once()
        mock_rag_service.process_document.assert_awaited_once()

    async def test_upload_no_files_raises_error(self):
        """Test that uploading with no files raises HTTPException."""
        with self.assertRaises(HTTPException) as cm:
            await upload_documents(files=[])

        self.assertEqual(cm.exception.status_code, 400)
        self.assertIn("No files provided", cm.exception.detail)

    async def test_upload_too_many_files_raises_error(self):
        """Test that uploading more than 5 files raises HTTPException."""
        mock_files = [MagicMock(spec=UploadFile) for _ in range(6)]

        with self.assertRaises(HTTPException) as cm:
            await upload_documents(files=mock_files)

        self.assertEqual(cm.exception.status_code, 400)
        self.assertIn("Too many files", cm.exception.detail)

    async def test_upload_invalid_file_type_raises_error(self):
        """Test that uploading invalid file type raises HTTPException."""
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "test.json"
        mock_file.content_type = "application/json"

        with self.assertRaises(HTTPException) as cm:
            await upload_documents(files=[mock_file])

        self.assertEqual(cm.exception.status_code, 400)
        self.assertIn("Invalid file type", cm.exception.detail)

    @patch("delpro_backend.routes.v1.documents_router.settings")
    async def test_upload_file_too_large_raises_error(self, mock_settings):
        """Test that uploading file larger than limit raises HTTPException."""
        mock_settings.MAX_FILE_SIZE_MB = 1  # 1 MB limit

        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "test.txt"
        mock_file.content_type = "text/plain"
        mock_file.read = AsyncMock(return_value=b"x" * (2 * 1024 * 1024))  # 2 MB

        with self.assertRaises(HTTPException) as cm:
            await upload_documents(files=[mock_file])

        self.assertEqual(cm.exception.status_code, 400)
        self.assertIn("too large", cm.exception.detail)


class TestDocumentsRouterList(unittest.IsolatedAsyncioTestCase):
    """Tests for list_documents endpoint."""

    @patch("delpro_backend.routes.v1.documents_router.DocumentService")
    async def test_list_documents_success(self, mock_doc_service):
        """Test listing documents returns JSON response."""
        mock_doc = MagicMock(spec=DocumentRow)
        mock_doc.id = "doc-1"
        mock_doc.filename = "file1.txt"
        mock_doc.content_type = "text/plain"
        mock_doc.file_size_bytes = 100
        mock_doc.upload_date = "2024-01-01"
        mock_doc.status = "completed"

        mock_doc_service.list_documents = AsyncMock(return_value=[(mock_doc, 5)])

        result = await list_documents()

        self.assertEqual(result.status_code, 200)

    @patch("delpro_backend.routes.v1.documents_router.DocumentService")
    async def test_list_documents_empty(self, mock_doc_service):
        """Test listing documents when no documents exist."""
        mock_doc_service.list_documents = AsyncMock(return_value=[])

        result = await list_documents()

        self.assertEqual(result.status_code, 200)


class TestDocumentsRouterGet(unittest.IsolatedAsyncioTestCase):
    """Tests for get_document endpoint."""

    @patch("delpro_backend.routes.v1.documents_router.DocumentService")
    async def test_get_document_success(self, mock_doc_service):
        """Test getting a single document."""
        mock_doc = MagicMock(spec=DocumentRow)
        mock_doc.id = "doc-123"
        mock_doc.filename = "test.txt"
        mock_doc.content_type = "text/plain"
        mock_doc.file_size_bytes = 100
        mock_doc.upload_date = "2024-01-01"
        mock_doc.status = "completed"

        mock_chunk = MagicMock(spec=ChunkRow)
        mock_chunk.content = "x" * 500  # Content longer than 400 chars

        mock_doc_service.get_document_with_chunks = AsyncMock(
            return_value=(mock_doc, [mock_chunk])
        )

        result = await get_document("doc-123")

        self.assertEqual(result.id, "doc-123")
        self.assertEqual(result.chunk_count, 1)
        # Chunk preview should be truncated
        self.assertTrue(result.chunks_preview[0].endswith("..."))

    @patch("delpro_backend.routes.v1.documents_router.DocumentService")
    async def test_get_document_not_found(self, mock_doc_service):
        """Test getting a non-existent document raises HTTPException."""
        mock_doc_service.get_document_with_chunks = AsyncMock(
            side_effect=ResourceNotFoundError("Document", "nonexistent")
        )

        with self.assertRaises(HTTPException) as cm:
            await get_document("nonexistent")

        self.assertEqual(cm.exception.status_code, 404)


class TestDocumentsRouterDelete(unittest.IsolatedAsyncioTestCase):
    """Tests for delete_document endpoint."""

    @patch("delpro_backend.routes.v1.documents_router.DocumentService")
    async def test_delete_document_success(self, mock_doc_service):
        """Test deleting a document."""
        mock_doc_service.delete_document = AsyncMock()

        result = await delete_document("doc-to-delete")

        self.assertEqual(result.status_code, 204)
        mock_doc_service.delete_document.assert_awaited_once_with("doc-to-delete")

    @patch("delpro_backend.routes.v1.documents_router.DocumentService")
    async def test_delete_document_not_found(self, mock_doc_service):
        """Test deleting a non-existent document raises HTTPException."""
        mock_doc_service.delete_document = AsyncMock(
            side_effect=ResourceNotFoundError("Document", "nonexistent")
        )

        with self.assertRaises(HTTPException) as cm:
            await delete_document("nonexistent")

        self.assertEqual(cm.exception.status_code, 404)
