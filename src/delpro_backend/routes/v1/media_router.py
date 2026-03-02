"""Router for media CRUD operations (images and PDFs)."""

from urllib.parse import quote

from fastapi import APIRouter, Form, Query, Response, UploadFile, status
from fastapi.responses import JSONResponse

from delpro_backend.models.v1.media_models import (
    GetMediaResponse,
    MediaListItem,
    UpdateMediaRequest,
)
from delpro_backend.services.media_service import MediaService
from delpro_backend.utils.builders import get_embeddings
from delpro_backend.utils.handle_errors import handle_errors
from delpro_backend.utils.logger import get_logger

logger_extra = {"component.name": "MediaRouter", "component.version": "v1"}
logger = get_logger(__name__)

media_router = APIRouter(prefix="/media", tags=["media"])

media_service = MediaService(embeddings=get_embeddings())


@media_router.post("")
@handle_errors
async def upload_media(file: UploadFile, description: str = Form(...)):
    """Upload a media file — JPEG, PNG, or PDF.

    Args:
        file: The media file.
        description: Free-text description for AI media selection.

    Returns:
        Upload confirmation with media metadata.
    """
    result = await media_service.create_media(file, description)

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=result.model_dump(),
    )


@media_router.get("")
@handle_errors
async def list_media(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=200),
):
    """List stored media with pagination (metadata only).

    Returns:
        Paginated list of media with metadata.
    """
    rows, total = await media_service.list_media(skip=skip, limit=limit)

    items = [
        MediaListItem(
            id=row.id,
            filename=row.filename,
            content_type=row.content_type,
            file_size_bytes=row.file_size_bytes,
            description=row.description,
            created_at=row.created_at,
        ).model_dump(mode="json")
        for row in rows
    ]

    return JSONResponse(status_code=status.HTTP_200_OK, content={"items": items, "total": total})


@media_router.get("/{media_id}")
@handle_errors
async def get_media(media_id: str):
    """Get metadata for a single media file.

    Args:
        media_id: The media UUID.

    Returns:
        Media metadata.
    """
    row = await media_service.get_media(media_id)

    return GetMediaResponse(
        id=row.id,
        filename=row.filename,
        content_type=row.content_type,
        file_size_bytes=row.file_size_bytes,
        description=row.description,
        created_at=row.created_at,
    )


@media_router.get("/{media_id}/content")
@handle_errors
async def get_media_content(media_id: str):
    """Return raw file bytes for preview/download.

    Args:
        media_id: The media UUID.

    Returns:
        Raw file bytes with correct Content-Type.
    """
    file_bytes, content_type, filename = await media_service.get_media_content(media_id)

    return Response(
        content=file_bytes,
        media_type=content_type,
        headers={"Content-Disposition": f"inline; filename*=UTF-8''{quote(filename)}"},
    )


@media_router.put("/{media_id}")
@handle_errors
async def update_media(media_id: str, data: UpdateMediaRequest):
    """Update media metadata (description and/or filename).

    Args:
        media_id: The media UUID.
        data: Fields to update.

    Returns:
        Updated media metadata.
    """
    row = await media_service.update_media(media_id, data)

    return GetMediaResponse(
        id=row.id,
        filename=row.filename,
        content_type=row.content_type,
        file_size_bytes=row.file_size_bytes,
        description=row.description,
        created_at=row.created_at,
    )


@media_router.put("/{media_id}/content")
@handle_errors
async def replace_media_content(media_id: str, file: UploadFile):
    """Replace the media file with a new upload.

    Args:
        media_id: The media UUID.
        file: New media file.

    Returns:
        Updated media metadata.
    """
    row = await media_service.replace_media_content(media_id, file)

    return GetMediaResponse(
        id=row.id,
        filename=row.filename,
        content_type=row.content_type,
        file_size_bytes=row.file_size_bytes,
        description=row.description,
        created_at=row.created_at,
    )


@media_router.delete("/{media_id}")
@handle_errors
async def delete_media(media_id: str):
    """Delete a media file.

    Args:
        media_id: The media UUID.

    Returns:
        204 No Content.
    """
    await media_service.delete_media(media_id)

    return Response(status_code=status.HTTP_204_NO_CONTENT)
