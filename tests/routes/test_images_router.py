"""Tests for images_router via TestClient."""

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


def _make_image_row(
    image_id="img-123",
    filename="photo.jpg",
    content_type="image/jpeg",
    file_size_bytes=100,
    description="A photo",
    created_at=None,
):
    """Create a MagicMock representing an ImageRow."""
    import datetime

    row = MagicMock()
    row.id = image_id
    row.filename = filename
    row.content_type = content_type
    row.file_size_bytes = file_size_bytes
    row.description = description
    row.created_at = created_at or datetime.datetime(2024, 1, 1)
    row.file_content = JPEG_BYTES
    return row


class TestImagesRouterUpload(unittest.TestCase):
    """Tests for POST /images upload endpoint."""

    def setUp(self):
        self.client = TestClient(app, raise_server_exceptions=False)

    @patch("delpro_backend.routes.v1.images_router.image_service")
    def test_upload_success_returns_201(self, mock_svc):
        """Test successful upload returns 201."""
        from delpro_backend.models.v1.image_models import UploadedImage

        mock_svc.create_image = AsyncMock(
            return_value=UploadedImage(
                id="img-123",
                filename="photo.jpg",
                file_size_bytes=len(JPEG_BYTES),
                description="A photo",
            )
        )

        response = self.client.post(
            "/images",
            files=[("file", ("photo.jpg", io.BytesIO(JPEG_BYTES), "image/jpeg"))],
            data={"description": "A photo"},
        )

        self.assertEqual(response.status_code, 201)

    @patch("delpro_backend.routes.v1.images_router.image_service")
    def test_upload_invalid_type_returns_400(self, mock_svc):
        """Test invalid file type returns 400."""
        mock_svc.create_image = AsyncMock(side_effect=InvalidRequestError("Only JPEG/PNG accepted"))

        response = self.client.post(
            "/images",
            files=[("file", ("photo.webp", io.BytesIO(b"RIFF\x00\x00\x00\x00WEBP"), "image/webp"))],
            data={"description": "webp"},
        )

        self.assertEqual(response.status_code, 400)

    @patch("delpro_backend.routes.v1.images_router.image_service")
    def test_upload_missing_file_returns_400(self, mock_svc):
        """Test missing file returns 400."""
        mock_svc.create_image = AsyncMock(
            side_effect=MissingParametersRequestError("file", "File is required")
        )

        response = self.client.post(
            "/images",
            files=[("file", ("x.jpg", io.BytesIO(b""), "image/jpeg"))],
            data={"description": "desc"},
        )

        self.assertEqual(response.status_code, 400)


class TestImagesRouterList(unittest.TestCase):
    """Tests for GET /images list endpoint."""

    def setUp(self):
        self.client = TestClient(app, raise_server_exceptions=False)

    @patch("delpro_backend.routes.v1.images_router.image_service")
    def test_list_returns_200(self, mock_svc):
        """Test listing images returns 200."""
        mock_svc.list_images = AsyncMock(return_value=[_make_image_row()])

        response = self.client.get("/images")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)

    @patch("delpro_backend.routes.v1.images_router.image_service")
    def test_list_returns_empty_200(self, mock_svc):
        """Test listing with no images returns empty list."""
        mock_svc.list_images = AsyncMock(return_value=[])

        response = self.client.get("/images")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])


class TestImagesRouterGet(unittest.TestCase):
    """Tests for GET /images/{image_id} endpoint."""

    def setUp(self):
        self.client = TestClient(app, raise_server_exceptions=False)

    @patch("delpro_backend.routes.v1.images_router.image_service")
    def test_get_image_returns_200(self, mock_svc):
        """Test getting an image returns 200."""
        mock_svc.get_image = AsyncMock(return_value=_make_image_row())

        response = self.client.get("/images/img-123")
        self.assertEqual(response.status_code, 200)

    @patch("delpro_backend.routes.v1.images_router.image_service")
    def test_get_image_not_found_returns_404(self, mock_svc):
        """Test getting a non-existent image returns 404."""
        mock_svc.get_image = AsyncMock(side_effect=ResourceNotFoundError("Image", "nonexistent"))

        response = self.client.get("/images/nonexistent")
        self.assertEqual(response.status_code, 404)


class TestImagesRouterGetContent(unittest.TestCase):
    """Tests for GET /images/{image_id}/content endpoint."""

    def setUp(self):
        self.client = TestClient(app, raise_server_exceptions=False)

    @patch("delpro_backend.routes.v1.images_router.image_service")
    def test_get_content_returns_bytes(self, mock_svc):
        """Test that image content is returned as bytes with correct content-type."""
        mock_svc.get_image_content = AsyncMock(
            return_value=(JPEG_BYTES, "image/jpeg", "photo.jpg")
        )

        response = self.client.get("/images/img-123/content")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, JPEG_BYTES)
        self.assertEqual(response.headers["content-type"], "image/jpeg")

    @patch("delpro_backend.routes.v1.images_router.image_service")
    def test_get_content_not_found_returns_404(self, mock_svc):
        """Test that non-existent image content returns 404."""
        mock_svc.get_image_content = AsyncMock(
            side_effect=ResourceNotFoundError("Image", "nonexistent")
        )

        response = self.client.get("/images/nonexistent/content")
        self.assertEqual(response.status_code, 404)


class TestImagesRouterUpdate(unittest.TestCase):
    """Tests for PUT /images/{image_id} endpoint."""

    def setUp(self):
        self.client = TestClient(app, raise_server_exceptions=False)

    @patch("delpro_backend.routes.v1.images_router.image_service")
    def test_update_image_returns_200(self, mock_svc):
        """Test updating an image returns 200."""
        mock_svc.update_image = AsyncMock(return_value=_make_image_row(description="new desc"))

        response = self.client.put(
            "/images/img-123",
            json={"description": "new desc"},
        )
        self.assertEqual(response.status_code, 200)

    @patch("delpro_backend.routes.v1.images_router.image_service")
    def test_update_image_not_found_returns_404(self, mock_svc):
        """Test updating a non-existent image returns 404."""
        mock_svc.update_image = AsyncMock(
            side_effect=ResourceNotFoundError("Image", "nonexistent")
        )

        response = self.client.put(
            "/images/nonexistent",
            json={"description": "x"},
        )
        self.assertEqual(response.status_code, 404)


class TestImagesRouterDelete(unittest.TestCase):
    """Tests for DELETE /images/{image_id} endpoint."""

    def setUp(self):
        self.client = TestClient(app, raise_server_exceptions=False)

    @patch("delpro_backend.routes.v1.images_router.image_service")
    def test_delete_image_returns_204(self, mock_svc):
        """Test deleting an image returns 204."""
        mock_svc.delete_image = AsyncMock()

        response = self.client.delete("/images/img-123")
        self.assertEqual(response.status_code, 204)

    @patch("delpro_backend.routes.v1.images_router.image_service")
    def test_delete_image_not_found_returns_404(self, mock_svc):
        """Test deleting a non-existent image returns 404."""
        mock_svc.delete_image = AsyncMock(
            side_effect=ResourceNotFoundError("Image", "nonexistent")
        )

        response = self.client.delete("/images/nonexistent")
        self.assertEqual(response.status_code, 404)
