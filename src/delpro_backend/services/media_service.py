"""Service for media CRUD operations (images and PDFs)."""

import io
from uuid import uuid4

from fastapi import UploadFile
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from PIL import Image
from sqlalchemy import select

from delpro_backend.db.db_service import AsyncSessionFactory
from delpro_backend.models.v1.database_models import MediaRow
from delpro_backend.models.v1.exception_models import (
    InvalidRequestError,
    MissingParametersRequestError,
    ResourceNotFoundError,
)
from delpro_backend.models.v1.media_models import UpdateMediaRequest, UploadedMedia
from delpro_backend.utils.logger import get_logger

logger_extra = {"component.name": "MediaService", "component.version": "v1"}
logger = get_logger(__name__)

_ALLOWED_MEDIA_TYPES = {"image/jpeg", "image/png", "application/pdf"}
_MAX_IMAGE_SIZE_MB = 5
_MAX_PDF_SIZE_MB = 20

_MAGIC_BYTES: list[tuple[bytes, str]] = [
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"%PDF", "application/pdf"),
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
        data: Raw file bytes.

    Returns:
        MIME type string, or None if not recognised.
    """
    for magic, mime in _MAGIC_BYTES:
        if data[: len(magic)] == magic:
            return mime
    return None


def _max_size_for_type(content_type: str) -> int:
    """Return the maximum allowed file size in MB for a given content type.

    Args:
        content_type: MIME type of the file.

    Returns:
        Maximum size in MB.
    """
    if content_type == "application/pdf":
        return _MAX_PDF_SIZE_MB
    return _MAX_IMAGE_SIZE_MB


class MediaService:
    """Service for media CRUD operations with semantic search."""

    def __init__(self, embeddings: GoogleGenerativeAIEmbeddings):
        """Initialize MediaService with embeddings model.

        Args:
            embeddings: Embeddings model for generating description vectors.
        """
        self._embeddings = embeddings

    async def create_media(self, file: UploadFile, description: str) -> UploadedMedia:
        """Upload and store a media file (image or PDF).

        WebP files are automatically converted to JPEG before storage.

        Args:
            file: Uploaded file (JPEG, PNG, WebP, or PDF).
            description: Free-text description used for semantic search.

        Returns:
            UploadedMedia with metadata.
        """
        if not file:
            raise MissingParametersRequestError()

        file_bytes = await file.read()
        file_size_mb = len(file_bytes) / (1024 * 1024)

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
            if actual_type is None or actual_type not in _ALLOWED_MEDIA_TYPES:
                raise InvalidRequestError(
                    "Only JPEG, PNG, WebP images, and PDF files are accepted."
                )
            content_type = actual_type

        max_size = _max_size_for_type(content_type)
        if file_size_mb > max_size:
            raise InvalidRequestError(
                f"File too large ({file_size_mb:.2f} MB). Maximum for {content_type}: {max_size} MB"
            )

        embedding = await self._embeddings.aembed_query(description)
        media_id = str(uuid4())

        async with AsyncSessionFactory() as session:
            row = MediaRow(
                id=media_id,
                filename=filename,
                content_type=content_type,
                file_size_bytes=len(file_bytes),
                file_content=file_bytes,
                description=description,
                embedding=embedding,
            )
            session.add(row)
            await session.commit()

        logger.info("Created media %s (%s)", media_id, filename, extra=logger_extra)

        return UploadedMedia(
            id=media_id,
            filename=filename,
            file_size_bytes=len(file_bytes),
            description=description,
        )

    async def list_media(self, skip: int = 0, limit: int = 20) -> tuple[list[MediaRow], int]:
        """List media with pagination (metadata only, no file content loaded eagerly).

        Returns:
            Tuple of (list of MediaRow objects, total count).
        """
        async with AsyncSessionFactory() as session:
            from sqlalchemy import func as sa_func

            count_stmt = select(sa_func.count()).select_from(MediaRow)
            total: int = (await session.execute(count_stmt)).scalar_one()
            stmt = select(MediaRow).order_by(MediaRow.created_at.desc()).offset(skip).limit(limit)
            result = await session.execute(stmt)
            return list(result.scalars().all()), total

    async def get_media(self, media_id: str) -> MediaRow:
        """Retrieve a media file by ID.

        Args:
            media_id: The media UUID.

        Returns:
            MediaRow.

        Raises:
            ResourceNotFoundError: If media not found.
        """
        async with AsyncSessionFactory() as session:
            row = await session.get(MediaRow, media_id)

        if not row:
            raise ResourceNotFoundError("Media", media_id)

        return row

    async def get_media_content(self, media_id: str) -> tuple[bytes, str, str]:
        """Retrieve raw file bytes for download/preview.

        Args:
            media_id: The media UUID.

        Returns:
            Tuple of (file_bytes, content_type, filename).

        Raises:
            ResourceNotFoundError: If media not found.
        """
        row = await self.get_media(media_id)
        return row.file_content, row.content_type, row.filename

    async def update_media(self, media_id: str, data: UpdateMediaRequest) -> MediaRow:
        """Update media metadata (description and/or filename).

        Re-embeds the description if it changes.

        Args:
            media_id: The media UUID.
            data: Fields to update.

        Returns:
            Updated MediaRow.

        Raises:
            ResourceNotFoundError: If media not found.
        """
        async with AsyncSessionFactory() as session:
            row = await session.get(MediaRow, media_id)
            if not row:
                raise ResourceNotFoundError("Media", media_id)

            if data.description is not None:
                row.description = data.description
                row.embedding = await self._embeddings.aembed_query(data.description)
            if data.filename is not None:
                row.filename = data.filename

            await session.commit()
            await session.refresh(row)

        logger.info("Updated media %s", media_id, extra=logger_extra)
        return row

    async def replace_media_content(self, media_id: str, file: UploadFile) -> MediaRow:
        """Replace the media file content, keeping existing metadata.

        Args:
            media_id: The media UUID.
            file: New file (JPEG, PNG, WebP, or PDF).

        Returns:
            Updated MediaRow.

        Raises:
            ResourceNotFoundError: If media not found.
            InvalidRequestError: If file type is invalid or too large.
        """
        if not file:
            raise MissingParametersRequestError()

        file_bytes = await file.read()
        file_size_mb = len(file_bytes) / (1024 * 1024)

        filename = file.filename or "untitled"

        if _is_webp(file_bytes):
            file_bytes = _convert_webp_to_jpeg(file_bytes)
            content_type = "image/jpeg"
            if filename.lower().endswith(".webp"):
                filename = filename[:-5] + ".jpg"
        else:
            actual_type = _detect_mime_type(file_bytes)
            if actual_type is None or actual_type not in _ALLOWED_MEDIA_TYPES:
                raise InvalidRequestError(
                    "Only JPEG, PNG, WebP images, and PDF files are accepted."
                )
            content_type = actual_type

        max_size = _max_size_for_type(content_type)
        if file_size_mb > max_size:
            raise InvalidRequestError(
                f"File too large ({file_size_mb:.2f} MB). Maximum for {content_type}: {max_size} MB"
            )

        async with AsyncSessionFactory() as session:
            row = await session.get(MediaRow, media_id)
            if not row:
                raise ResourceNotFoundError("Media", media_id)

            row.file_content = file_bytes
            row.file_size_bytes = len(file_bytes)
            row.content_type = content_type
            row.filename = filename

            await session.commit()
            await session.refresh(row)

        logger.info("Replaced media content %s", media_id, extra=logger_extra)
        return row

    async def delete_media(self, media_id: str) -> None:
        """Delete a media file.

        Args:
            media_id: The media UUID.

        Raises:
            ResourceNotFoundError: If media not found.
        """
        async with AsyncSessionFactory() as session:
            row = await session.get(MediaRow, media_id)
            if not row:
                raise ResourceNotFoundError("Media", media_id)

            await session.delete(row)
            await session.commit()

        logger.info("Deleted media %s", media_id, extra=logger_extra)

    async def search_media_by_description(self, description: str) -> MediaRow | None:
        """Find the most semantically similar media using cosine distance.

        Args:
            description: Natural-language description of the desired media.

        Returns:
            The best matching MediaRow with all fields loaded, or None if no media exist.
        """
        query_vec = await self._embeddings.aembed_query(description)

        async with AsyncSessionFactory() as session:
            stmt = (
                select(MediaRow)
                .where(MediaRow.embedding.isnot(None))
                .order_by(MediaRow.embedding.cosine_distance(query_vec))
                .limit(1)
            )
            row = await session.scalar(stmt)
            if row is not None:
                # Force-load file_content while the session is still open,
                # so the detached object has the bytes available after session close.
                _ = row.file_content
            return row
