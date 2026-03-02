"""Tests for media_router via TestClient."""

import io
import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from tests.keys_test import DEFAULT_KEYS

for key, value in DEFAULT_KEYS.items():
    os.environ.setdefault(key, value)

from delpro_backend.main import app  # noqa: E402
from delpro_backend.models.v1.exception_models import (  # noqa: E402
    InvalidRequestError,
    MissingParametersRequestError,
    ResourceNotFoundError,
)

JPEG_BYTES = b"\xff\xd8\xff" + b"x" * 100
PDF_BYTES = b"%PDF-1.4" + b"x" * 100


def _make_media_row(
    media_id="media-123",
    filename="photo.jpg",
    content_type="image/jpeg",
    file_size_bytes=100,
    description="A photo",
    created_at=None,
):
    """Create a MagicMock representing a MediaRow."""
    import datetime

    row = MagicMock()
    row.id = media_id
    row.filename = filename
    row.content_type = content_type
    row.file_size_bytes = file_size_bytes
    row.description = description
    row.created_at = created_at or datetime.datetime(2024, 1, 1)
    row.file_content = JPEG_BYTES
    return row


class TestMediaRouterUpload(unittest.TestCase):
    """Tests for POST /media upload endpoint."""

    def setUp(self):
        self.client = TestClient(app, raise_server_exceptions=False)

    @patch("delpro_backend.routes.v1.media_router.media_service")
    def test_upload_success_returns_201(self, mock_svc):
        """Test successful upload returns 201."""
        from delpro_backend.models.v1.media_models import UploadedMedia

        mock_svc.create_media = AsyncMock(
            return_value=UploadedMedia(
                id="media-123",
                filename="photo.jpg",
                file_size_bytes=len(JPEG_BYTES),
                description="A photo",
            )
        )

        response = self.client.post(
            "/media",
            files=[("file", ("photo.jpg", io.BytesIO(JPEG_BYTES), "image/jpeg"))],
            data={"description": "A photo"},
        )

        self.assertEqual(response.status_code, 201)

    @patch("delpro_backend.routes.v1.media_router.media_service")
    def test_upload_pdf_returns_201(self, mock_svc):
        """Test successful PDF upload returns 201."""
        from delpro_backend.models.v1.media_models import UploadedMedia

        mock_svc.create_media = AsyncMock(
            return_value=UploadedMedia(
                id="media-456",
                filename="document.pdf",
                file_size_bytes=len(PDF_BYTES),
                description="A PDF",
            )
        )

        response = self.client.post(
            "/media",
            files=[("file", ("document.pdf", io.BytesIO(PDF_BYTES), "application/pdf"))],
            data={"description": "A PDF"},
        )

        self.assertEqual(response.status_code, 201)

    @patch("delpro_backend.routes.v1.media_router.media_service")
    def test_upload_invalid_type_returns_400(self, mock_svc):
        """Test invalid file type returns 400."""
        mock_svc.create_media = AsyncMock(
            side_effect=InvalidRequestError("Only JPEG/PNG/PDF accepted")
        )

        response = self.client.post(
            "/media",
            files=[("file", ("photo.webp", io.BytesIO(b"RIFF\x00\x00\x00\x00WEBP"), "image/webp"))],
            data={"description": "webp"},
        )

        self.assertEqual(response.status_code, 400)

    @patch("delpro_backend.routes.v1.media_router.media_service")
    def test_upload_missing_file_returns_400(self, mock_svc):
        """Test missing file returns 400."""
        mock_svc.create_media = AsyncMock(
            side_effect=MissingParametersRequestError("file", "File is required")
        )

        response = self.client.post(
            "/media",
            files=[("file", ("x.jpg", io.BytesIO(b""), "image/jpeg"))],
            data={"description": "desc"},
        )

        self.assertEqual(response.status_code, 400)


class TestMediaRouterList(unittest.TestCase):
    """Tests for GET /media list endpoint."""

    def setUp(self):
        self.client = TestClient(app, raise_server_exceptions=False)

    @patch("delpro_backend.routes.v1.media_router.media_service")
    def test_list_returns_200(self, mock_svc):
        """Test listing media returns 200 with paginated envelope."""
        mock_svc.list_media = AsyncMock(return_value=([_make_media_row()], 1))

        response = self.client.get("/media")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["total"], 1)
        self.assertEqual(len(body["items"]), 1)

    @patch("delpro_backend.routes.v1.media_router.media_service")
    def test_list_returns_empty_200(self, mock_svc):
        """Test listing with no media returns empty paginated envelope."""
        mock_svc.list_media = AsyncMock(return_value=([], 0))

        response = self.client.get("/media")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["items"], [])
        self.assertEqual(body["total"], 0)

    @patch("delpro_backend.routes.v1.media_router.media_service")
    def test_list_pagination_params(self, mock_svc):
        """Test skip/limit query params are forwarded to service."""
        mock_svc.list_media = AsyncMock(return_value=([], 42))

        response = self.client.get("/media?skip=20&limit=20")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["total"], 42)
        mock_svc.list_media.assert_awaited_once_with(skip=20, limit=20)


class TestMediaRouterGet(unittest.TestCase):
    """Tests for GET /media/{media_id} endpoint."""

    def setUp(self):
        self.client = TestClient(app, raise_server_exceptions=False)

    @patch("delpro_backend.routes.v1.media_router.media_service")
    def test_get_media_returns_200(self, mock_svc):
        """Test getting media returns 200."""
        mock_svc.get_media = AsyncMock(return_value=_make_media_row())

        response = self.client.get("/media/media-123")
        self.assertEqual(response.status_code, 200)

    @patch("delpro_backend.routes.v1.media_router.media_service")
    def test_get_media_not_found_returns_404(self, mock_svc):
        """Test getting non-existent media returns 404."""
        mock_svc.get_media = AsyncMock(side_effect=ResourceNotFoundError("Media", "nonexistent"))

        response = self.client.get("/media/nonexistent")
        self.assertEqual(response.status_code, 404)


class TestMediaRouterGetContent(unittest.TestCase):
    """Tests for GET /media/{media_id}/content endpoint."""

    def setUp(self):
        self.client = TestClient(app, raise_server_exceptions=False)

    @patch("delpro_backend.routes.v1.media_router.media_service")
    def test_get_content_returns_bytes(self, mock_svc):
        """Test that media content is returned as bytes with correct content-type."""
        mock_svc.get_media_content = AsyncMock(
            return_value=(JPEG_BYTES, "image/jpeg", "photo.jpg")
        )

        response = self.client.get("/media/media-123/content")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, JPEG_BYTES)
        self.assertEqual(response.headers["content-type"], "image/jpeg")

    @patch("delpro_backend.routes.v1.media_router.media_service")
    def test_get_pdf_content_returns_application_pdf(self, mock_svc):
        """Test that PDF content is returned with correct content-type."""
        mock_svc.get_media_content = AsyncMock(
            return_value=(PDF_BYTES, "application/pdf", "document.pdf")
        )

        response = self.client.get("/media/media-456/content")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, PDF_BYTES)
        self.assertEqual(response.headers["content-type"], "application/pdf")

    @patch("delpro_backend.routes.v1.media_router.media_service")
    def test_get_content_not_found_returns_404(self, mock_svc):
        """Test that non-existent media content returns 404."""
        mock_svc.get_media_content = AsyncMock(
            side_effect=ResourceNotFoundError("Media", "nonexistent")
        )

        response = self.client.get("/media/nonexistent/content")
        self.assertEqual(response.status_code, 404)


class TestMediaRouterUpdate(unittest.TestCase):
    """Tests for PUT /media/{media_id} endpoint."""

    def setUp(self):
        self.client = TestClient(app, raise_server_exceptions=False)

    @patch("delpro_backend.routes.v1.media_router.media_service")
    def test_update_media_returns_200(self, mock_svc):
        """Test updating media returns 200."""
        mock_svc.update_media = AsyncMock(return_value=_make_media_row(description="new desc"))

        response = self.client.put(
            "/media/media-123",
            json={"description": "new desc"},
        )
        self.assertEqual(response.status_code, 200)

    @patch("delpro_backend.routes.v1.media_router.media_service")
    def test_update_media_not_found_returns_404(self, mock_svc):
        """Test updating non-existent media returns 404."""
        mock_svc.update_media = AsyncMock(
            side_effect=ResourceNotFoundError("Media", "nonexistent")
        )

        response = self.client.put(
            "/media/nonexistent",
            json={"description": "x"},
        )
        self.assertEqual(response.status_code, 404)


class TestMediaRouterDelete(unittest.TestCase):
    """Tests for DELETE /media/{media_id} endpoint."""

    def setUp(self):
        self.client = TestClient(app, raise_server_exceptions=False)

    @patch("delpro_backend.routes.v1.media_router.media_service")
    def test_delete_media_returns_204(self, mock_svc):
        """Test deleting media returns 204."""
        mock_svc.delete_media = AsyncMock()

        response = self.client.delete("/media/media-123")
        self.assertEqual(response.status_code, 204)

    @patch("delpro_backend.routes.v1.media_router.media_service")
    def test_delete_media_not_found_returns_404(self, mock_svc):
        """Test deleting non-existent media returns 404."""
        mock_svc.delete_media = AsyncMock(
            side_effect=ResourceNotFoundError("Media", "nonexistent")
        )

        response = self.client.delete("/media/nonexistent")
        self.assertEqual(response.status_code, 404)
