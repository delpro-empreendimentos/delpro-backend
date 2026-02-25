"""Service for image CRUD operations."""

import io
from uuid import uuid4

from fastapi import UploadFile
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from PIL import Image
from sqlalchemy import select

from delpro_backend.db.db_service import AsyncSessionFactory
from delpro_backend.models.v1.database_models import ImageRow
from delpro_backend.models.v1.exception_models import (
    InvalidRequestError,
    MissingParametersRequestError,
    ResourceNotFoundError,
)
from delpro_backend.models.v1.image_models import UpdateImageRequest, UploadedImage
from delpro_backend.utils.logger import get_logger

logger_extra = {"component.name": "ImageService", "component.version": "v1"}
logger = get_logger(__name__)

_ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png"}
_MAX_IMAGE_SIZE_MB = 5

_MAGIC_BYTES: list[tuple[bytes, str]] = [
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
]


def _is_webp(data: bytes) -> bool:
    """Return True if *data* is a WebP image.

    WebP files start with b'RIFF', followed by 4 bytes of variable file-size,
    then b'WEBP' — so a simple prefix match is not sufficient.

    Args:
        data: Raw image bytes.

    Returns:
        True if the magic bytes match WebP, False otherwise.
    """
    return len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP"


def _convert_webp_to_jpeg(data: bytes) -> bytes:
    """Convert WebP image bytes to JPEG.

    RGBA/palette images are flattened onto a white background before encoding,
    because JPEG does not support transparency.

    Args:
        data: Raw WebP image bytes.

    Returns:
        JPEG-encoded image bytes.
    """
    with Image.open(io.BytesIO(data)) as img:
        if img.mode in ("RGBA", "LA", "P"):
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img.convert("RGBA"), mask=img.convert("RGBA").split()[-1])
            img = background
        elif img.mode != "RGB":
            img = img.convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=90)
        return buf.getvalue()


def _detect_mime_type(data: bytes) -> str | None:
    """Detect MIME type from magic bytes.

    Args:
        data: Raw image bytes.

    Returns:
        MIME type string, or None if not recognised.
    """
    for magic, mime in _MAGIC_BYTES:
        if data[: len(magic)] == magic:
            return mime
    return None


class ImageService:
    """Service for image CRUD operations with semantic search."""

    def __init__(self, embeddings: GoogleGenerativeAIEmbeddings):
        """Initialize ImageService with embeddings model.

        Args:
            embeddings: Embeddings model for generating description vectors.
        """
        self._embeddings = embeddings

    async def create_image(self, file: UploadFile, description: str) -> UploadedImage:
        """Upload and store an image.

        WebP files are automatically converted to JPEG before storage.

        Args:
            file: Uploaded image file (JPEG, PNG, or WebP, max 5 MB).
            description: Free-text description used for semantic search.

        Returns:
            UploadedImage with metadata.
        """
        if not file:
            raise MissingParametersRequestError()

        file_bytes = await file.read()
        file_size_mb = len(file_bytes) / (1024 * 1024)

        if file_size_mb > _MAX_IMAGE_SIZE_MB:
            raise InvalidRequestError(
                f"Image too large ({file_size_mb:.2f} MB). Maximum: {_MAX_IMAGE_SIZE_MB} MB"
            )

        filename = file.filename or "untitled"

        # Detect real type from magic bytes — the client-declared Content-Type can be wrong.
        # WebP is detected separately because its magic bytes are not a plain prefix.
        if _is_webp(file_bytes):
            file_bytes = _convert_webp_to_jpeg(file_bytes)
            content_type = "image/jpeg"
            if filename.lower().endswith(".webp"):
                filename = filename[:-5] + ".jpg"
        else:
            actual_type = _detect_mime_type(file_bytes)
            if actual_type is None or actual_type not in _ALLOWED_IMAGE_TYPES:
                raise InvalidRequestError("Only JPEG, PNG, and WebP images are accepted.")
            content_type = actual_type

        embedding = await self._embeddings.aembed_query(description)
        image_id = str(uuid4())

        async with AsyncSessionFactory() as session:
            row = ImageRow(
                id=image_id,
                filename=filename,
                content_type=content_type,
                file_size_bytes=len(file_bytes),
                file_content=file_bytes,
                description=description,
                embedding=embedding,
            )
            session.add(row)
            await session.commit()

        logger.info("Created image %s (%s)", image_id, filename, extra=logger_extra)

        return UploadedImage(
            id=image_id,
            filename=filename,
            file_size_bytes=len(file_bytes),
            description=description,
        )

    async def list_images(self) -> list[ImageRow]:
        """List all images (metadata only, no file content loaded eagerly).

        Returns:
            List of ImageRow objects.
        """
        async with AsyncSessionFactory() as session:
            stmt = select(ImageRow).order_by(ImageRow.created_at.desc())
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def get_image(self, image_id: str) -> ImageRow:
        """Retrieve an image by ID.

        Args:
            image_id: The image UUID.

        Returns:
            ImageRow.

        Raises:
            ResourceNotFoundError: If image not found.
        """
        async with AsyncSessionFactory() as session:
            row = await session.get(ImageRow, image_id)

        if not row:
            raise ResourceNotFoundError("Image", image_id)

        return row

    async def get_image_content(self, image_id: str) -> tuple[bytes, str, str]:
        """Retrieve raw image bytes for download/preview.

        Args:
            image_id: The image UUID.

        Returns:
            Tuple of (file_bytes, content_type, filename).

        Raises:
            ResourceNotFoundError: If image not found.
        """
        row = await self.get_image(image_id)
        return row.file_content, row.content_type, row.filename

    async def update_image(self, image_id: str, data: UpdateImageRequest) -> ImageRow:
        """Update image metadata (description and/or filename).

        Re-embeds the description if it changes.

        Args:
            image_id: The image UUID.
            data: Fields to update.

        Returns:
            Updated ImageRow.

        Raises:
            ResourceNotFoundError: If image not found.
        """
        async with AsyncSessionFactory() as session:
            row = await session.get(ImageRow, image_id)
            if not row:
                raise ResourceNotFoundError("Image", image_id)

            if data.description is not None:
                row.description = data.description
                row.embedding = await self._embeddings.aembed_query(data.description)
            if data.filename is not None:
                row.filename = data.filename

            await session.commit()
            await session.refresh(row)

        logger.info("Updated image %s", image_id, extra=logger_extra)
        return row

    async def replace_image_content(self, image_id: str, file: UploadFile) -> ImageRow:
        """Replace the image file content, keeping existing metadata.

        Args:
            image_id: The image UUID.
            file: New image file (JPEG, PNG, or WebP).

        Returns:
            Updated ImageRow.

        Raises:
            ResourceNotFoundError: If image not found.
            InvalidRequestError: If file type is invalid or too large.
        """
        if not file:
            raise MissingParametersRequestError()

        file_bytes = await file.read()
        file_size_mb = len(file_bytes) / (1024 * 1024)

        if file_size_mb > _MAX_IMAGE_SIZE_MB:
            raise InvalidRequestError(
                f"Image too large ({file_size_mb:.2f} MB). Maximum: {_MAX_IMAGE_SIZE_MB} MB"
            )

        filename = file.filename or "untitled"

        if _is_webp(file_bytes):
            file_bytes = _convert_webp_to_jpeg(file_bytes)
            content_type = "image/jpeg"
            if filename.lower().endswith(".webp"):
                filename = filename[:-5] + ".jpg"
        else:
            actual_type = _detect_mime_type(file_bytes)
            if actual_type is None or actual_type not in _ALLOWED_IMAGE_TYPES:
                raise InvalidRequestError("Only JPEG, PNG, and WebP images are accepted.")
            content_type = actual_type

        async with AsyncSessionFactory() as session:
            row = await session.get(ImageRow, image_id)
            if not row:
                raise ResourceNotFoundError("Image", image_id)

            row.file_content = file_bytes
            row.file_size_bytes = len(file_bytes)
            row.content_type = content_type
            row.filename = filename

            await session.commit()
            await session.refresh(row)

        logger.info("Replaced image content %s", image_id, extra=logger_extra)
        return row

    async def delete_image(self, image_id: str) -> None:
        """Delete an image.

        Args:
            image_id: The image UUID.

        Raises:
            ResourceNotFoundError: If image not found.
        """
        async with AsyncSessionFactory() as session:
            row = await session.get(ImageRow, image_id)
            if not row:
                raise ResourceNotFoundError("Image", image_id)

            await session.delete(row)
            await session.commit()

        logger.info("Deleted image %s", image_id, extra=logger_extra)

    async def search_image_by_description(self, description: str) -> ImageRow | None:
        """Find the most semantically similar image using cosine distance.

        Args:
            description: Natural-language description of the desired image.

        Returns:
            The best matching ImageRow with all fields loaded, or None if no images exist.
        """
        query_vec = await self._embeddings.aembed_query(description)

        async with AsyncSessionFactory() as session:
            stmt = (
                select(ImageRow)
                .where(ImageRow.embedding.isnot(None))
                .order_by(ImageRow.embedding.cosine_distance(query_vec))
                .limit(1)
            )
            row = await session.scalar(stmt)
            if row is not None:
                # Force-load file_content while the session is still open,
                # so the detached object has the bytes available after session close.
                _ = row.file_content
            return row
