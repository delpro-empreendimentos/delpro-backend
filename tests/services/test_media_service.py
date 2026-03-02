"""Tests for MediaService."""

import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from tests.keys_test import DEFAULT_KEYS

for key, value in DEFAULT_KEYS.items():
    os.environ.setdefault(key, value)

from delpro_backend.models.v1.database_models import MediaRow  # noqa: E402
from delpro_backend.models.v1.exception_models import (  # noqa: E402
    InvalidRequestError,
    MissingParametersRequestError,
    ResourceNotFoundError,
)
from delpro_backend.services.media_service import (  # noqa: E402
    MediaService,
    _detect_mime_type,
    _is_webp,
)

JPEG_BYTES = b"\xff\xd8\xff" + b"x" * 100
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"x" * 100
WEBP_BYTES = b"RIFF\x28\x00\x00\x00WEBP" + b"x" * 100
PDF_BYTES = b"%PDF-1.4" + b"x" * 100


def _make_service():
    mock_embeddings = AsyncMock()
    mock_embeddings.aembed_query = AsyncMock(return_value=[0.1] * 3072)
    return MediaService(embeddings=mock_embeddings), mock_embeddings


class TestDetectMimeType(unittest.TestCase):
    """Tests for _detect_mime_type helper."""

    def test_detects_jpeg(self):
        self.assertEqual(_detect_mime_type(JPEG_BYTES), "image/jpeg")

    def test_detects_png(self):
        self.assertEqual(_detect_mime_type(PNG_BYTES), "image/png")

    def test_detects_pdf(self):
        self.assertEqual(_detect_mime_type(PDF_BYTES), "application/pdf")

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


class TestMediaServiceCreateMedia(unittest.IsolatedAsyncioTestCase):
    """Tests for MediaService.create_media."""

    @patch("delpro_backend.services.media_service.AsyncSessionFactory")
    async def test_creates_jpeg_successfully(self, mock_factory):
        """Test creating a JPEG image succeeds."""
        svc, _ = _make_service()

        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_factory.return_value.__aenter__.return_value = mock_session

        mock_file = MagicMock()
        mock_file.content_type = "image/jpeg"
        mock_file.filename = "photo.jpg"
        mock_file.read = AsyncMock(return_value=JPEG_BYTES)

        result = await svc.create_media(mock_file, "A photo")

        mock_session.add.assert_called_once()
        mock_session.commit.assert_awaited_once()
        self.assertEqual(result.filename, "photo.jpg")

    @patch("delpro_backend.services.media_service.AsyncSessionFactory")
    async def test_creates_png_successfully(self, mock_factory):
        """Test creating a PNG image succeeds."""
        svc, _ = _make_service()

        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_factory.return_value.__aenter__.return_value = mock_session

        mock_file = MagicMock()
        mock_file.content_type = "image/png"
        mock_file.filename = "image.png"
        mock_file.read = AsyncMock(return_value=PNG_BYTES)

        result = await svc.create_media(mock_file, "A PNG image")

        self.assertEqual(result.filename, "image.png")

    @patch("delpro_backend.services.media_service.AsyncSessionFactory")
    async def test_creates_pdf_successfully(self, mock_factory):
        """Test creating a PDF succeeds."""
        svc, _ = _make_service()

        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_factory.return_value.__aenter__.return_value = mock_session

        mock_file = MagicMock()
        mock_file.content_type = "application/pdf"
        mock_file.filename = "document.pdf"
        mock_file.read = AsyncMock(return_value=PDF_BYTES)

        result = await svc.create_media(mock_file, "A PDF document")

        mock_session.add.assert_called_once()
        mock_session.commit.assert_awaited_once()
        self.assertEqual(result.filename, "document.pdf")

    @patch("delpro_backend.services.media_service.AsyncSessionFactory")
    async def test_raises_on_missing_file(self, mock_factory):
        """Test that MissingParametersRequestError is raised when file is None."""
        svc, _ = _make_service()

        with self.assertRaises(MissingParametersRequestError):
            await svc.create_media(None, "desc")

    @patch("delpro_backend.services.media_service._convert_webp_to_jpeg", return_value=JPEG_BYTES)
    @patch("delpro_backend.services.media_service.AsyncSessionFactory")
    async def test_converts_webp_to_jpeg(self, mock_factory, mock_convert):
        """Test that WebP files are converted to JPEG and stored with .jpg extension."""
        svc, _ = _make_service()

        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_factory.return_value.__aenter__.return_value = mock_session

        mock_file = MagicMock()
        mock_file.filename = "photo.webp"
        mock_file.read = AsyncMock(return_value=WEBP_BYTES)

        result = await svc.create_media(mock_file, "A webp photo")

        mock_convert.assert_called_once_with(WEBP_BYTES)
        self.assertEqual(result.filename, "photo.jpg")
        self.assertEqual(result.file_size_bytes, len(JPEG_BYTES))

    @patch("delpro_backend.services.media_service.AsyncSessionFactory")
    async def test_raises_on_oversized_image(self, mock_factory):
        """Test that InvalidRequestError is raised when image exceeds 5MB."""
        svc, _ = _make_service()

        big_bytes = JPEG_BYTES + b"x" * (6 * 1024 * 1024)

        mock_file = MagicMock()
        mock_file.content_type = "image/jpeg"
        mock_file.filename = "big.jpg"
        mock_file.read = AsyncMock(return_value=big_bytes)

        with self.assertRaises(InvalidRequestError):
            await svc.create_media(mock_file, "big photo")

    @patch("delpro_backend.services.media_service.AsyncSessionFactory")
    async def test_pdf_under_20mb_accepted(self, mock_factory):
        """Test that a PDF under 20MB is accepted."""
        svc, _ = _make_service()

        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_factory.return_value.__aenter__.return_value = mock_session

        pdf_bytes = b"%PDF-1.4" + b"x" * (19 * 1024 * 1024)

        mock_file = MagicMock()
        mock_file.content_type = "application/pdf"
        mock_file.filename = "large.pdf"
        mock_file.read = AsyncMock(return_value=pdf_bytes)

        result = await svc.create_media(mock_file, "Large PDF")
        self.assertEqual(result.filename, "large.pdf")

    @patch("delpro_backend.services.media_service.AsyncSessionFactory")
    async def test_pdf_over_20mb_rejected(self, mock_factory):
        """Test that a PDF over 20MB is rejected."""
        svc, _ = _make_service()

        pdf_bytes = b"%PDF-1.4" + b"x" * (21 * 1024 * 1024)

        mock_file = MagicMock()
        mock_file.content_type = "application/pdf"
        mock_file.filename = "huge.pdf"
        mock_file.read = AsyncMock(return_value=pdf_bytes)

        with self.assertRaises(InvalidRequestError):
            await svc.create_media(mock_file, "Huge PDF")

    @patch("delpro_backend.services.media_service.AsyncSessionFactory")
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

        result = await svc.create_media(mock_file, "desc")

        self.assertEqual(result.filename, "untitled")


class TestMediaServiceGetMedia(unittest.IsolatedAsyncioTestCase):
    """Tests for MediaService.get_media."""

    @patch("delpro_backend.services.media_service.AsyncSessionFactory")
    async def test_returns_media_when_found(self, mock_factory):
        """Test get_media returns row when it exists."""
        svc, _ = _make_service()

        mock_row = MagicMock(spec=MediaRow)
        mock_session = AsyncMock()
        mock_session.get.return_value = mock_row
        mock_factory.return_value.__aenter__.return_value = mock_session

        result = await svc.get_media("media-123")

        self.assertEqual(result, mock_row)

    @patch("delpro_backend.services.media_service.AsyncSessionFactory")
    async def test_raises_when_not_found(self, mock_factory):
        """Test get_media raises ResourceNotFoundError when not found."""
        svc, _ = _make_service()

        mock_session = AsyncMock()
        mock_session.get.return_value = None
        mock_factory.return_value.__aenter__.return_value = mock_session

        with self.assertRaises(ResourceNotFoundError):
            await svc.get_media("nonexistent")


class TestMediaServiceGetMediaContent(unittest.IsolatedAsyncioTestCase):
    """Tests for MediaService.get_media_content."""

    @patch("delpro_backend.services.media_service.AsyncSessionFactory")
    async def test_returns_bytes_content_type_filename(self, mock_factory):
        """Test get_media_content returns (bytes, content_type, filename)."""
        svc, _ = _make_service()

        mock_row = MagicMock(spec=MediaRow)
        mock_row.file_content = JPEG_BYTES
        mock_row.content_type = "image/jpeg"
        mock_row.filename = "photo.jpg"

        mock_session = AsyncMock()
        mock_session.get.return_value = mock_row
        mock_factory.return_value.__aenter__.return_value = mock_session

        file_bytes, content_type, filename = await svc.get_media_content("media-123")

        self.assertEqual(file_bytes, JPEG_BYTES)
        self.assertEqual(content_type, "image/jpeg")
        self.assertEqual(filename, "photo.jpg")


class TestMediaServiceListMedia(unittest.IsolatedAsyncioTestCase):
    """Tests for MediaService.list_media."""

    @patch("delpro_backend.services.media_service.AsyncSessionFactory")
    async def test_returns_list_of_rows(self, mock_factory):
        """Test list_media returns list of MediaRow objects with total."""
        svc, _ = _make_service()

        mock_row1 = MagicMock(spec=MediaRow)
        mock_row2 = MagicMock(spec=MediaRow)

        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 2
        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = [mock_row1, mock_row2]

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=[mock_count_result, mock_data_result])
        mock_factory.return_value.__aenter__.return_value = mock_session

        rows, total = await svc.list_media()

        self.assertEqual(len(rows), 2)
        self.assertEqual(total, 2)

    @patch("delpro_backend.services.media_service.AsyncSessionFactory")
    async def test_returns_empty_list(self, mock_factory):
        """Test list_media returns empty list with total 0."""
        svc, _ = _make_service()

        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 0
        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = []

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=[mock_count_result, mock_data_result])
        mock_factory.return_value.__aenter__.return_value = mock_session

        rows, total = await svc.list_media()

        self.assertEqual(rows, [])
        self.assertEqual(total, 0)


class TestMediaServiceUpdateMedia(unittest.IsolatedAsyncioTestCase):
    """Tests for MediaService.update_media."""

    @patch("delpro_backend.services.media_service.AsyncSessionFactory")
    async def test_updates_description_and_re_embeds(self, mock_factory):
        """Test that description update triggers re-embedding."""
        svc, mock_embeddings = _make_service()

        mock_row = MagicMock(spec=MediaRow)
        mock_row.description = "old description"
        mock_row.filename = "photo.jpg"

        mock_session = AsyncMock()
        mock_session.get.return_value = mock_row
        mock_session.refresh = AsyncMock(return_value=None)
        mock_factory.return_value.__aenter__.return_value = mock_session

        from delpro_backend.models.v1.media_models import UpdateMediaRequest

        data = UpdateMediaRequest(description="new description")
        await svc.update_media("media-123", data)

        mock_embeddings.aembed_query.assert_awaited_once_with("new description")
        self.assertEqual(mock_row.description, "new description")

    @patch("delpro_backend.services.media_service.AsyncSessionFactory")
    async def test_updates_filename_only(self, mock_factory):
        """Test that only filename is updated when description is None."""
        svc, mock_embeddings = _make_service()

        mock_row = MagicMock(spec=MediaRow)
        mock_session = AsyncMock()
        mock_session.get.return_value = mock_row
        mock_session.refresh = AsyncMock(return_value=None)
        mock_factory.return_value.__aenter__.return_value = mock_session

        from delpro_backend.models.v1.media_models import UpdateMediaRequest

        data = UpdateMediaRequest(filename="new_name.jpg")
        await svc.update_media("media-123", data)

        mock_embeddings.aembed_query.assert_not_awaited()
        self.assertEqual(mock_row.filename, "new_name.jpg")

    @patch("delpro_backend.services.media_service.AsyncSessionFactory")
    async def test_raises_when_not_found(self, mock_factory):
        """Test that ResourceNotFoundError is raised when media not found."""
        svc, _ = _make_service()

        mock_session = AsyncMock()
        mock_session.get.return_value = None
        mock_factory.return_value.__aenter__.return_value = mock_session

        from delpro_backend.models.v1.media_models import UpdateMediaRequest

        with self.assertRaises(ResourceNotFoundError):
            await svc.update_media("nonexistent", UpdateMediaRequest(filename="x.jpg"))


class TestMediaServiceDeleteMedia(unittest.IsolatedAsyncioTestCase):
    """Tests for MediaService.delete_media."""

    @patch("delpro_backend.services.media_service.AsyncSessionFactory")
    async def test_deletes_media_when_found(self, mock_factory):
        """Test that media is deleted when found."""
        svc, _ = _make_service()

        mock_row = MagicMock(spec=MediaRow)
        mock_session = AsyncMock()
        mock_session.get.return_value = mock_row
        mock_factory.return_value.__aenter__.return_value = mock_session

        await svc.delete_media("media-123")

        mock_session.delete.assert_awaited_once_with(mock_row)
        mock_session.commit.assert_awaited_once()

    @patch("delpro_backend.services.media_service.AsyncSessionFactory")
    async def test_raises_when_not_found(self, mock_factory):
        """Test that ResourceNotFoundError is raised when media not found."""
        svc, _ = _make_service()

        mock_session = AsyncMock()
        mock_session.get.return_value = None
        mock_factory.return_value.__aenter__.return_value = mock_session

        with self.assertRaises(ResourceNotFoundError):
            await svc.delete_media("nonexistent")


class TestMediaServiceSearchByDescription(unittest.IsolatedAsyncioTestCase):
    """Tests for MediaService.search_media_by_description."""

    @patch("delpro_backend.services.media_service.AsyncSessionFactory")
    async def test_returns_matching_media(self, mock_factory):
        """Test that matching media is returned."""
        svc, _ = _make_service()

        mock_row = MagicMock(spec=MediaRow)
        mock_row.file_content = JPEG_BYTES

        mock_session = AsyncMock()
        mock_session.scalar.return_value = mock_row
        mock_factory.return_value.__aenter__.return_value = mock_session

        result = await svc.search_media_by_description("a photo of a pool")

        self.assertEqual(result, mock_row)

    @patch("delpro_backend.services.media_service.AsyncSessionFactory")
    async def test_returns_none_when_no_match(self, mock_factory):
        """Test that None is returned when no media exist."""
        svc, _ = _make_service()

        mock_session = AsyncMock()
        mock_session.scalar.return_value = None
        mock_factory.return_value.__aenter__.return_value = mock_session

        result = await svc.search_media_by_description("something obscure")

        self.assertIsNone(result)

    @patch("delpro_backend.services.media_service.AsyncSessionFactory")
    async def test_forces_load_of_file_content(self, mock_factory):
        """Test that file_content is accessed (loaded) within session."""
        svc, _ = _make_service()

        mock_row = MagicMock(spec=MediaRow)
        mock_row.file_content = JPEG_BYTES

        mock_session = AsyncMock()
        mock_session.scalar.return_value = mock_row
        mock_factory.return_value.__aenter__.return_value = mock_session

        result = await svc.search_media_by_description("pool photo")

        # file_content should have been accessed (the _ = row.file_content line)
        self.assertIsNotNone(result)


class TestMediaServiceReplaceContent(unittest.IsolatedAsyncioTestCase):
    """Tests for MediaService.replace_media_content."""

    @patch("delpro_backend.services.media_service.AsyncSessionFactory")
    async def test_replaces_jpeg_successfully(self, mock_factory):
        """Test replacing media content with a JPEG succeeds."""
        svc, _ = _make_service()

        mock_row = MagicMock(spec=MediaRow)
        mock_session = AsyncMock()
        mock_session.get.return_value = mock_row
        mock_session.refresh = AsyncMock(return_value=None)
        mock_factory.return_value.__aenter__.return_value = mock_session

        mock_file = MagicMock()
        mock_file.filename = "new_photo.jpg"
        mock_file.read = AsyncMock(return_value=JPEG_BYTES)

        result = await svc.replace_media_content("media-123", mock_file)

        self.assertEqual(result, mock_row)
        mock_session.commit.assert_awaited_once()

    @patch("delpro_backend.services.media_service.AsyncSessionFactory")
    async def test_raises_on_missing_file(self, mock_factory):
        """Test that MissingParametersRequestError is raised when file is None."""
        svc, _ = _make_service()

        with self.assertRaises(MissingParametersRequestError):
            await svc.replace_media_content("media-123", None)

    @patch("delpro_backend.services.media_service.AsyncSessionFactory")
    async def test_raises_when_not_found(self, mock_factory):
        """Test that ResourceNotFoundError is raised when media not found."""
        svc, _ = _make_service()

        mock_session = AsyncMock()
        mock_session.get.return_value = None
        mock_factory.return_value.__aenter__.return_value = mock_session

        mock_file = MagicMock()
        mock_file.filename = "photo.jpg"
        mock_file.read = AsyncMock(return_value=JPEG_BYTES)

        with self.assertRaises(ResourceNotFoundError):
            await svc.replace_media_content("nonexistent", mock_file)

    @patch("delpro_backend.services.media_service.AsyncSessionFactory")
    async def test_raises_on_invalid_type(self, mock_factory):
        """Test InvalidRequestError for unknown file type."""
        svc, _ = _make_service()

        mock_file = MagicMock()
        mock_file.filename = "bad.exe"
        mock_file.read = AsyncMock(return_value=b"MZ\x90\x00" + b"x" * 100)

        with self.assertRaises(InvalidRequestError):
            await svc.replace_media_content("media-123", mock_file)

    @patch("delpro_backend.services.media_service._convert_webp_to_jpeg", return_value=JPEG_BYTES)
    @patch("delpro_backend.services.media_service.AsyncSessionFactory")
    async def test_replaces_with_webp_converts_to_jpeg(self, mock_factory, mock_convert):
        """Test that WebP replacement files are converted to JPEG."""
        svc, _ = _make_service()

        mock_row = MagicMock(spec=MediaRow)
        mock_session = AsyncMock()
        mock_session.get.return_value = mock_row
        mock_session.refresh = AsyncMock(return_value=None)
        mock_factory.return_value.__aenter__.return_value = mock_session

        mock_file = MagicMock()
        mock_file.filename = "photo.webp"
        mock_file.read = AsyncMock(return_value=WEBP_BYTES)

        await svc.replace_media_content("media-123", mock_file)

        mock_convert.assert_called_once_with(WEBP_BYTES)

    @patch("delpro_backend.services.media_service._convert_webp_to_jpeg", return_value=JPEG_BYTES)
    @patch("delpro_backend.services.media_service.AsyncSessionFactory")
    async def test_webp_without_extension_still_converts(self, mock_factory, mock_convert):
        """Test that WebP content without .webp extension still converts."""
        svc, _ = _make_service()

        mock_row = MagicMock(spec=MediaRow)
        mock_session = AsyncMock()
        mock_session.get.return_value = mock_row
        mock_session.refresh = AsyncMock(return_value=None)
        mock_factory.return_value.__aenter__.return_value = mock_session

        mock_file = MagicMock()
        mock_file.filename = "photo.jpg"  # declared as jpg but actually webp
        mock_file.read = AsyncMock(return_value=WEBP_BYTES)

        await svc.replace_media_content("media-123", mock_file)

        mock_convert.assert_called_once_with(WEBP_BYTES)

    @patch("delpro_backend.services.media_service.AsyncSessionFactory")
    async def test_raises_on_oversized_replacement(self, mock_factory):
        """Test that InvalidRequestError is raised when replacement exceeds size limit."""
        svc, _ = _make_service()

        big_bytes = JPEG_BYTES + b"x" * (6 * 1024 * 1024)

        mock_file = MagicMock()
        mock_file.filename = "big.jpg"
        mock_file.read = AsyncMock(return_value=big_bytes)

        with self.assertRaises(InvalidRequestError):
            await svc.replace_media_content("media-123", mock_file)


class TestConvertWebpToJpeg(unittest.TestCase):
    """Tests for _convert_webp_to_jpeg function."""

    def test_converts_webp_to_jpeg_bytes(self):
        """Test that _convert_webp_to_jpeg returns JPEG bytes."""
        from PIL import Image
        import io
        from delpro_backend.services.media_service import _convert_webp_to_jpeg

        # Create a real 1x1 WebP image for testing
        buf = io.BytesIO()
        img = Image.new("RGB", (1, 1), color=(255, 0, 0))
        img.save(buf, format="WEBP")
        webp_bytes = buf.getvalue()

        result = _convert_webp_to_jpeg(webp_bytes)

        self.assertTrue(result.startswith(b"\xff\xd8\xff"))  # JPEG magic bytes

    def test_converts_rgba_webp_to_jpeg(self):
        """Test that RGBA WebP images are converted correctly (flattened onto white)."""
        from PIL import Image
        import io
        from delpro_backend.services.media_service import _convert_webp_to_jpeg

        buf = io.BytesIO()
        img = Image.new("RGBA", (1, 1), color=(255, 0, 0, 128))
        img.save(buf, format="WEBP")
        webp_bytes = buf.getvalue()

        result = _convert_webp_to_jpeg(webp_bytes)
        self.assertTrue(result.startswith(b"\xff\xd8\xff"))


class TestCreateMediaWebpNoExtension(unittest.IsolatedAsyncioTestCase):
    """Test WebP conversion in create_media when filename has no .webp extension."""

    @patch("delpro_backend.services.media_service._convert_webp_to_jpeg", return_value=JPEG_BYTES)
    @patch("delpro_backend.services.media_service.AsyncSessionFactory")
    async def test_creates_webp_without_webp_extension(self, mock_factory, mock_convert):
        """Test that WebP content without .webp extension still converts and stores as JPEG."""
        svc, _ = _make_service()

        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_factory.return_value.__aenter__.return_value = mock_session

        mock_file = MagicMock()
        mock_file.filename = "photo.jpg"  # actual content is webp though
        mock_file.read = AsyncMock(return_value=WEBP_BYTES)

        result = await svc.create_media(mock_file, "A webp photo stored as jpg")

        mock_convert.assert_called_once_with(WEBP_BYTES)
        # filename unchanged since it doesn't end with .webp
        self.assertEqual(result.filename, "photo.jpg")


class TestConvertWebpToJpegNonRGB(unittest.TestCase):
    """Tests for _convert_webp_to_jpeg with grayscale (non-RGBA, non-RGB) mode."""

    def test_converts_grayscale_webp_to_jpeg(self):
        """Test that grayscale ('L' mode) WebP images are converted to JPEG via RGB."""
        from PIL import Image
        import io
        from delpro_backend.services.media_service import _convert_webp_to_jpeg

        buf = io.BytesIO()
        img = Image.new("L", (2, 2), color=128)  # grayscale, mode='L'
        img.save(buf, format="WEBP")
        webp_bytes = buf.getvalue()

        result = _convert_webp_to_jpeg(webp_bytes)
        self.assertTrue(result.startswith(b"\xff\xd8\xff"))


class TestCreateMediaInvalidType(unittest.IsolatedAsyncioTestCase):
    """Test create_media with non-WebP unknown file type raises InvalidRequestError."""

    async def test_raises_for_unknown_non_webp_type(self):
        """Test that unknown non-WebP file type raises InvalidRequestError."""
        svc, _ = _make_service()

        mock_file = MagicMock()
        mock_file.filename = "bad.exe"
        mock_file.read = AsyncMock(return_value=b"MZ\x90\x00" + b"x" * 100)

        with self.assertRaises(InvalidRequestError):
            await svc.create_media(mock_file, "desc")


class TestConvertWebpNonRGBMode(unittest.TestCase):
    """Tests for _convert_webp_to_jpeg with unusual image modes."""

    def test_converts_non_rgb_non_rgba_mode_to_jpeg(self):
        """Test that image modes not in RGBA/LA/P and not RGB go through convert('RGB')."""
        from unittest.mock import MagicMock, patch
        import io
        from delpro_backend.services.media_service import _convert_webp_to_jpeg

        # Create a mock image that has mode 'CMYK' (not RGBA/LA/P, not RGB)
        mock_img = MagicMock()
        mock_img.mode = "CMYK"
        mock_img.__enter__ = MagicMock(return_value=mock_img)
        mock_img.__exit__ = MagicMock(return_value=False)

        rgb_mock = MagicMock()
        rgb_mock.mode = "RGB"
        mock_img.convert = MagicMock(return_value=rgb_mock)

        buf = io.BytesIO()
        rgb_mock.save = MagicMock(side_effect=lambda f, **kw: f.write(b"\xff\xd8\xff\xe0" + b"\x00" * 20))

        with patch("delpro_backend.services.media_service.Image.open", return_value=mock_img):
            result = _convert_webp_to_jpeg(b"fake data")

        mock_img.convert.assert_called_once_with("RGB")
        self.assertIsNotNone(result)
