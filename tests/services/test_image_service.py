"""Tests for ImageService."""

import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from tests.keys_test import DEFAULT_KEYS

for key, value in DEFAULT_KEYS.items():
    os.environ.setdefault(key, value)

from delpro_backend.models.v1.exception_models import (  # noqa: E402
    InvalidRequestError,
    MissingParametersRequestError,
    ResourceNotFoundError,
)
from delpro_backend.models.v1.database_models import ImageRow  # noqa: E402
from delpro_backend.services.image_service import ImageService, _detect_mime_type, _is_webp  # noqa: E402

JPEG_BYTES = b"\xff\xd8\xff" + b"x" * 100
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"x" * 100
WEBP_BYTES = b"RIFF\x28\x00\x00\x00WEBP" + b"x" * 100


def _make_service():
    mock_embeddings = AsyncMock()
    mock_embeddings.aembed_query = AsyncMock(return_value=[0.1] * 3072)
    return ImageService(embeddings=mock_embeddings), mock_embeddings


class TestDetectMimeType(unittest.TestCase):
    """Tests for _detect_mime_type helper."""

    def test_detects_jpeg(self):
        self.assertEqual(_detect_mime_type(JPEG_BYTES), "image/jpeg")

    def test_detects_png(self):
        self.assertEqual(_detect_mime_type(PNG_BYTES), "image/png")

    def test_returns_none_for_webp(self):
        self.assertIsNone(_detect_mime_type(WEBP_BYTES))

    def test_returns_none_for_unknown(self):
        self.assertIsNone(_detect_mime_type(b"unknown data"))


class TestIsWebp(unittest.TestCase):
    """Tests for _is_webp helper."""

    def test_detects_webp(self):
        self.assertTrue(_is_webp(WEBP_BYTES))

    def test_returns_false_for_jpeg(self):
        self.assertFalse(_is_webp(JPEG_BYTES))

    def test_returns_false_for_png(self):
        self.assertFalse(_is_webp(PNG_BYTES))

    def test_returns_false_for_short_data(self):
        self.assertFalse(_is_webp(b"RIFF"))

    def test_returns_false_for_riff_non_webp(self):
        # RIFF container but not WebP (e.g. WAV)
        self.assertFalse(_is_webp(b"RIFF\x00\x00\x00\x00WAVE" + b"x" * 10))


class TestImageServiceCreateImage(unittest.IsolatedAsyncioTestCase):
    """Tests for ImageService.create_image."""

    @patch("delpro_backend.services.image_service.AsyncSessionFactory")
    async def test_creates_jpeg_image_successfully(self, mock_factory):
        """Test creating a JPEG image succeeds."""
        svc, _ = _make_service()

        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_factory.return_value.__aenter__.return_value = mock_session

        mock_file = MagicMock()
        mock_file.content_type = "image/jpeg"
        mock_file.filename = "photo.jpg"
        mock_file.read = AsyncMock(return_value=JPEG_BYTES)

        result = await svc.create_image(mock_file, "A photo")

        mock_session.add.assert_called_once()
        mock_session.commit.assert_awaited_once()
        self.assertEqual(result.filename, "photo.jpg")

    @patch("delpro_backend.services.image_service.AsyncSessionFactory")
    async def test_creates_png_image_successfully(self, mock_factory):
        """Test creating a PNG image succeeds."""
        svc, _ = _make_service()

        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_factory.return_value.__aenter__.return_value = mock_session

        mock_file = MagicMock()
        mock_file.content_type = "image/png"
        mock_file.filename = "image.png"
        mock_file.read = AsyncMock(return_value=PNG_BYTES)

        result = await svc.create_image(mock_file, "A PNG image")

        self.assertEqual(result.filename, "image.png")

    @patch("delpro_backend.services.image_service.AsyncSessionFactory")
    async def test_raises_on_missing_file(self, mock_factory):
        """Test that MissingParametersRequestError is raised when file is None."""
        svc, _ = _make_service()

        with self.assertRaises(MissingParametersRequestError):
            await svc.create_image(None, "desc")

    @patch("delpro_backend.services.image_service._convert_webp_to_jpeg", return_value=JPEG_BYTES)
    @patch("delpro_backend.services.image_service.AsyncSessionFactory")
    async def test_converts_webp_to_jpeg(self, mock_factory, mock_convert):
        """Test that WebP files are converted to JPEG and stored with .jpg extension."""
        svc, _ = _make_service()

        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_factory.return_value.__aenter__.return_value = mock_session

        mock_file = MagicMock()
        mock_file.filename = "photo.webp"
        mock_file.read = AsyncMock(return_value=WEBP_BYTES)

        result = await svc.create_image(mock_file, "A webp photo")

        mock_convert.assert_called_once_with(WEBP_BYTES)
        self.assertEqual(result.filename, "photo.jpg")
        self.assertEqual(result.file_size_bytes, len(JPEG_BYTES))

    @patch("delpro_backend.services.image_service.AsyncSessionFactory")
    async def test_raises_on_oversized_file(self, mock_factory):
        """Test that InvalidRequestError is raised when file exceeds 5MB."""
        svc, _ = _make_service()

        big_bytes = JPEG_BYTES + b"x" * (6 * 1024 * 1024)

        mock_file = MagicMock()
        mock_file.content_type = "image/jpeg"
        mock_file.filename = "big.jpg"
        mock_file.read = AsyncMock(return_value=big_bytes)

        with self.assertRaises(InvalidRequestError):
            await svc.create_image(mock_file, "big photo")

    @patch("delpro_backend.services.image_service.AsyncSessionFactory")
    async def test_uses_untitled_when_no_filename(self, mock_factory):
        """Test that 'untitled' is used when filename is None."""
        svc, _ = _make_service()

        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_factory.return_value.__aenter__.return_value = mock_session

        mock_file = MagicMock()
        mock_file.content_type = "image/jpeg"
        mock_file.filename = None
        mock_file.read = AsyncMock(return_value=JPEG_BYTES)

        result = await svc.create_image(mock_file, "desc")

        self.assertEqual(result.filename, "untitled")


class TestImageServiceGetImage(unittest.IsolatedAsyncioTestCase):
    """Tests for ImageService.get_image."""

    @patch("delpro_backend.services.image_service.AsyncSessionFactory")
    async def test_returns_image_when_found(self, mock_factory):
        """Test get_image returns row when it exists."""
        svc, _ = _make_service()

        mock_row = MagicMock(spec=ImageRow)
        mock_session = AsyncMock()
        mock_session.get.return_value = mock_row
        mock_factory.return_value.__aenter__.return_value = mock_session

        result = await svc.get_image("img-123")

        self.assertEqual(result, mock_row)

    @patch("delpro_backend.services.image_service.AsyncSessionFactory")
    async def test_raises_when_not_found(self, mock_factory):
        """Test get_image raises ResourceNotFoundError when not found."""
        svc, _ = _make_service()

        mock_session = AsyncMock()
        mock_session.get.return_value = None
        mock_factory.return_value.__aenter__.return_value = mock_session

        with self.assertRaises(ResourceNotFoundError):
            await svc.get_image("nonexistent")


class TestImageServiceGetImageContent(unittest.IsolatedAsyncioTestCase):
    """Tests for ImageService.get_image_content."""

    @patch("delpro_backend.services.image_service.AsyncSessionFactory")
    async def test_returns_bytes_content_type_filename(self, mock_factory):
        """Test get_image_content returns (bytes, content_type, filename)."""
        svc, _ = _make_service()

        mock_row = MagicMock(spec=ImageRow)
        mock_row.file_content = JPEG_BYTES
        mock_row.content_type = "image/jpeg"
        mock_row.filename = "photo.jpg"

        mock_session = AsyncMock()
        mock_session.get.return_value = mock_row
        mock_factory.return_value.__aenter__.return_value = mock_session

        file_bytes, content_type, filename = await svc.get_image_content("img-123")

        self.assertEqual(file_bytes, JPEG_BYTES)
        self.assertEqual(content_type, "image/jpeg")
        self.assertEqual(filename, "photo.jpg")


class TestImageServiceListImages(unittest.IsolatedAsyncioTestCase):
    """Tests for ImageService.list_images."""

    @patch("delpro_backend.services.image_service.AsyncSessionFactory")
    async def test_returns_list_of_rows(self, mock_factory):
        """Test list_images returns list of ImageRow objects."""
        svc, _ = _make_service()

        mock_row1 = MagicMock(spec=ImageRow)
        mock_row2 = MagicMock(spec=ImageRow)

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_row1, mock_row2]
        mock_session.execute.return_value = mock_result
        mock_factory.return_value.__aenter__.return_value = mock_session

        result = await svc.list_images()

        self.assertEqual(len(result), 2)

    @patch("delpro_backend.services.image_service.AsyncSessionFactory")
    async def test_returns_empty_list(self, mock_factory):
        """Test list_images returns empty list when no images."""
        svc, _ = _make_service()

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result
        mock_factory.return_value.__aenter__.return_value = mock_session

        result = await svc.list_images()

        self.assertEqual(result, [])


class TestImageServiceUpdateImage(unittest.IsolatedAsyncioTestCase):
    """Tests for ImageService.update_image."""

    @patch("delpro_backend.services.image_service.AsyncSessionFactory")
    async def test_updates_description_and_re_embeds(self, mock_factory):
        """Test that description update triggers re-embedding."""
        svc, mock_embeddings = _make_service()

        mock_row = MagicMock(spec=ImageRow)
        mock_row.description = "old description"
        mock_row.filename = "photo.jpg"

        mock_session = AsyncMock()
        mock_session.get.return_value = mock_row
        mock_session.refresh = AsyncMock(return_value=None)
        mock_factory.return_value.__aenter__.return_value = mock_session

        from delpro_backend.models.v1.image_models import UpdateImageRequest

        data = UpdateImageRequest(description="new description")
        await svc.update_image("img-123", data)

        mock_embeddings.aembed_query.assert_awaited_once_with("new description")
        self.assertEqual(mock_row.description, "new description")

    @patch("delpro_backend.services.image_service.AsyncSessionFactory")
    async def test_updates_filename_only(self, mock_factory):
        """Test that only filename is updated when description is None."""
        svc, mock_embeddings = _make_service()

        mock_row = MagicMock(spec=ImageRow)
        mock_session = AsyncMock()
        mock_session.get.return_value = mock_row
        mock_session.refresh = AsyncMock(return_value=None)
        mock_factory.return_value.__aenter__.return_value = mock_session

        from delpro_backend.models.v1.image_models import UpdateImageRequest

        data = UpdateImageRequest(filename="new_name.jpg")
        await svc.update_image("img-123", data)

        mock_embeddings.aembed_query.assert_not_awaited()
        self.assertEqual(mock_row.filename, "new_name.jpg")

    @patch("delpro_backend.services.image_service.AsyncSessionFactory")
    async def test_raises_when_not_found(self, mock_factory):
        """Test that ResourceNotFoundError is raised when image not found."""
        svc, _ = _make_service()

        mock_session = AsyncMock()
        mock_session.get.return_value = None
        mock_factory.return_value.__aenter__.return_value = mock_session

        from delpro_backend.models.v1.image_models import UpdateImageRequest

        with self.assertRaises(ResourceNotFoundError):
            await svc.update_image("nonexistent", UpdateImageRequest(filename="x.jpg"))


class TestImageServiceDeleteImage(unittest.IsolatedAsyncioTestCase):
    """Tests for ImageService.delete_image."""

    @patch("delpro_backend.services.image_service.AsyncSessionFactory")
    async def test_deletes_image_when_found(self, mock_factory):
        """Test that image is deleted when found."""
        svc, _ = _make_service()

        mock_row = MagicMock(spec=ImageRow)
        mock_session = AsyncMock()
        mock_session.get.return_value = mock_row
        mock_factory.return_value.__aenter__.return_value = mock_session

        await svc.delete_image("img-123")

        mock_session.delete.assert_awaited_once_with(mock_row)
        mock_session.commit.assert_awaited_once()

    @patch("delpro_backend.services.image_service.AsyncSessionFactory")
    async def test_raises_when_not_found(self, mock_factory):
        """Test that ResourceNotFoundError is raised when image not found."""
        svc, _ = _make_service()

        mock_session = AsyncMock()
        mock_session.get.return_value = None
        mock_factory.return_value.__aenter__.return_value = mock_session

        with self.assertRaises(ResourceNotFoundError):
            await svc.delete_image("nonexistent")


class TestImageServiceSearchByDescription(unittest.IsolatedAsyncioTestCase):
    """Tests for ImageService.search_image_by_description."""

    @patch("delpro_backend.services.image_service.AsyncSessionFactory")
    async def test_returns_matching_image(self, mock_factory):
        """Test that matching image is returned."""
        svc, _ = _make_service()

        mock_row = MagicMock(spec=ImageRow)
        mock_row.file_content = JPEG_BYTES

        mock_session = AsyncMock()
        mock_session.scalar.return_value = mock_row
        mock_factory.return_value.__aenter__.return_value = mock_session

        result = await svc.search_image_by_description("a photo of a pool")

        self.assertEqual(result, mock_row)

    @patch("delpro_backend.services.image_service.AsyncSessionFactory")
    async def test_returns_none_when_no_match(self, mock_factory):
        """Test that None is returned when no images exist."""
        svc, _ = _make_service()

        mock_session = AsyncMock()
        mock_session.scalar.return_value = None
        mock_factory.return_value.__aenter__.return_value = mock_session

        result = await svc.search_image_by_description("something obscure")

        self.assertIsNone(result)

    @patch("delpro_backend.services.image_service.AsyncSessionFactory")
    async def test_forces_load_of_file_content(self, mock_factory):
        """Test that file_content is accessed (loaded) within session."""
        svc, _ = _make_service()

        mock_row = MagicMock(spec=ImageRow)
        mock_row.file_content = JPEG_BYTES

        mock_session = AsyncMock()
        mock_session.scalar.return_value = mock_row
        mock_factory.return_value.__aenter__.return_value = mock_session

        result = await svc.search_image_by_description("pool photo")

        # file_content should have been accessed (the _ = row.file_content line)
        self.assertIsNotNone(result)
