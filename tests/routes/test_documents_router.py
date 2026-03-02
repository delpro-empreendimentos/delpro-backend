"""Tests for documents_router via TestClient."""

import os
import io
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from tests.keys_test import DEFAULT_KEYS

for key, value in DEFAULT_KEYS.items():
    os.environ.setdefault(key, value)

from delpro_backend.main import app  # noqa: E402
from delpro_backend.models.v1.document_models import UploadedDocument  # noqa: E402
from delpro_backend.models.v1.exception_models import ResourceNotFoundError  # noqa: E402


class TestDocumentsRouterUpload(unittest.TestCase):
    """Tests for POST /documents upload endpoint."""

    def setUp(self):
        self.client = TestClient(app, raise_server_exceptions=False)

    @patch("delpro_backend.routes.v1.documents_router.document_service")
    def test_upload_success_returns_201(self, mock_svc):
        """Test successful upload returns 201."""
        mock_svc.create_document = AsyncMock(
            return_value=[
                UploadedDocument(
                    id="doc-1",
                    filename="test.txt",
                    file_size_bytes=11,
                    status="completed",
                    chunk_count=1,
                )
            ]
        )

        response = self.client.post(
            "/documents",
            files=[("files", ("test.txt", io.BytesIO(b"hello world"), "text/plain"))],
        )

        self.assertEqual(response.status_code, 201)

    @patch("delpro_backend.routes.v1.documents_router.document_service")
    def test_upload_document_processing_error_returns_500(self, mock_svc):
        """Test that DocumentProcessingError returns 500."""
        from delpro_backend.models.v1.exception_models import DocumentProcessingError

        mock_svc.create_document = AsyncMock(
            side_effect=DocumentProcessingError("doc-1", "parse error")
        )

        response = self.client.post(
            "/documents",
            files=[("files", ("test.txt", io.BytesIO(b"content"), "text/plain"))],
        )

        self.assertEqual(response.status_code, 500)

    @patch("delpro_backend.routes.v1.documents_router.document_service")
    def test_upload_invalid_type_returns_400(self, mock_svc):
        """Test that invalid file type returns 400."""
        from delpro_backend.models.v1.exception_models import InvalidRequestError

        mock_svc.create_document = AsyncMock(
            side_effect=InvalidRequestError("Only txt/pdf accepted")
        )

        response = self.client.post(
            "/documents",
            files=[("files", ("test.json", io.BytesIO(b"{}"), "application/json"))],
        )

        self.assertEqual(response.status_code, 400)


class TestDocumentsRouterList(unittest.TestCase):
    """Tests for GET /documents list endpoint."""

    def setUp(self):
        self.client = TestClient(app, raise_server_exceptions=False)

    @patch("delpro_backend.routes.v1.documents_router.document_service")
    def test_list_returns_200(self, mock_svc):
        """Test listing documents returns 200 with paginated envelope."""
        mock_doc = MagicMock()
        mock_doc.id = "doc-1"
        mock_doc.filename = "test.txt"
        mock_doc.content_type = "text/plain"
        mock_doc.file_size_bytes = 100
        mock_doc.upload_date = "2024-01-01T00:00:00"
        mock_doc.status = "completed"

        mock_svc.list_documents = AsyncMock(return_value=([(mock_doc, 3)], 1))

        response = self.client.get("/documents")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["total"], 1)
        self.assertEqual(len(body["items"]), 1)

    @patch("delpro_backend.routes.v1.documents_router.document_service")
    def test_list_returns_empty_200(self, mock_svc):
        """Test listing with no documents returns 200 with empty paginated envelope."""
        mock_svc.list_documents = AsyncMock(return_value=([], 0))

        response = self.client.get("/documents")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["items"], [])
        self.assertEqual(body["total"], 0)

    @patch("delpro_backend.routes.v1.documents_router.document_service")
    def test_list_pagination_params(self, mock_svc):
        """Test skip/limit query params are forwarded to service."""
        mock_svc.list_documents = AsyncMock(return_value=([], 15))

        response = self.client.get("/documents?skip=0&limit=20")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["total"], 15)
        mock_svc.list_documents.assert_awaited_once_with(skip=0, limit=20)


class TestDocumentsRouterGet(unittest.TestCase):
    """Tests for GET /documents/{id} endpoint."""

    def setUp(self):
        self.client = TestClient(app, raise_server_exceptions=False)

    @patch("delpro_backend.routes.v1.documents_router.document_service")
    def test_get_document_returns_200(self, mock_svc):
        """Test getting a document returns 200."""
        import datetime

        mock_doc = MagicMock()
        mock_doc.id = "doc-123"
        mock_doc.filename = "test.txt"
        mock_doc.content_type = "text/plain"
        mock_doc.file_size_bytes = 100
        mock_doc.upload_date = datetime.datetime(2024, 1, 1)
        mock_doc.status = "completed"

        mock_chunk = MagicMock()
        mock_chunk.content = "x" * 500

        mock_svc.get_document_with_chunks = AsyncMock(return_value=(mock_doc, [mock_chunk]))

        response = self.client.get("/documents/doc-123")
        self.assertEqual(response.status_code, 200)

    @patch("delpro_backend.routes.v1.documents_router.document_service")
    def test_get_document_not_found_returns_404(self, mock_svc):
        """Test getting a non-existent document returns 404."""
        mock_svc.get_document_with_chunks = AsyncMock(
            side_effect=ResourceNotFoundError("Document", "nonexistent")
        )

        response = self.client.get("/documents/nonexistent")
        self.assertEqual(response.status_code, 404)


class TestDocumentsRouterDelete(unittest.TestCase):
    """Tests for DELETE /documents/{id} endpoint."""

    def setUp(self):
        self.client = TestClient(app, raise_server_exceptions=False)

    @patch("delpro_backend.routes.v1.documents_router.document_service")
    def test_delete_document_returns_204(self, mock_svc):
        """Test deleting a document returns 204."""
        mock_svc.delete_document = AsyncMock()

        response = self.client.delete("/documents/doc-to-delete")
        self.assertEqual(response.status_code, 204)

    @patch("delpro_backend.routes.v1.documents_router.document_service")
    def test_delete_document_not_found_returns_404(self, mock_svc):
        """Test deleting a non-existent document returns 404."""
        mock_svc.delete_document = AsyncMock(
            side_effect=ResourceNotFoundError("Document", "nonexistent")
        )

        response = self.client.delete("/documents/nonexistent")
        self.assertEqual(response.status_code, 404)
