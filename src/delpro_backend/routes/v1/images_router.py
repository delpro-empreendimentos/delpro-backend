"""Router for image CRUD operations."""

from urllib.parse import quote

from fastapi import APIRouter, Form, Response, UploadFile, status
from fastapi.responses import JSONResponse

from delpro_backend.models.v1.image_models import (
    GetImageResponse,
    ImageListItem,
    UpdateImageRequest,
)
from delpro_backend.services.image_service import ImageService
from delpro_backend.utils.builders import get_embeddings
from delpro_backend.utils.handle_errors import handle_errors
from delpro_backend.utils.logger import get_logger

logger_extra = {"component.name": "ImagesRouter", "component.version": "v1"}
logger = get_logger(__name__)

images_router = APIRouter(prefix="/images", tags=["images"])

image_service = ImageService(embeddings=get_embeddings())


@images_router.post("")
@handle_errors
async def upload_image(file: UploadFile, description: str = Form(...)):
    """Upload a JPEG or PNG image (max 5 MB).

    Args:
        file: The image file.
        description: Free-text description for AI image selection.

    Returns:
        Upload confirmation with image metadata.
    """
    result = await image_service.create_image(file, description)

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=result.model_dump(),
    )


@images_router.get("")
@handle_errors
async def list_images():
    """List all stored images (metadata only).

    Returns:
        List of images with metadata.
    """
    rows = await image_service.list_images()

    items = [
        ImageListItem(
            id=row.id,
            filename=row.filename,
            content_type=row.content_type,
            file_size_bytes=row.file_size_bytes,
            description=row.description,
            created_at=row.created_at,
        ).model_dump(mode="json")
        for row in rows
    ]

    return JSONResponse(status_code=status.HTTP_200_OK, content=items)


@images_router.get("/{image_id}")
@handle_errors
async def get_image(image_id: str):
    """Get metadata for a single image.

    Args:
        image_id: The image UUID.

    Returns:
        Image metadata.
    """
    row = await image_service.get_image(image_id)

    return GetImageResponse(
        id=row.id,
        filename=row.filename,
        content_type=row.content_type,
        file_size_bytes=row.file_size_bytes,
        description=row.description,
        created_at=row.created_at,
    )


@images_router.get("/{image_id}/content")
@handle_errors
async def get_image_content(image_id: str):
    """Return raw image bytes for preview/download.

    Args:
        image_id: The image UUID.

    Returns:
        Raw image bytes with correct Content-Type.
    """
    file_bytes, content_type, filename = await image_service.get_image_content(image_id)

    return Response(
        content=file_bytes,
        media_type=content_type,
        headers={"Content-Disposition": f"inline; filename*=UTF-8''{quote(filename)}"},
    )


@images_router.put("/{image_id}")
@handle_errors
async def update_image(image_id: str, data: UpdateImageRequest):
    """Update image metadata (description and/or filename).

    Args:
        image_id: The image UUID.
        data: Fields to update.

    Returns:
        Updated image metadata.
    """
    row = await image_service.update_image(image_id, data)

    return GetImageResponse(
        id=row.id,
        filename=row.filename,
        content_type=row.content_type,
        file_size_bytes=row.file_size_bytes,
        description=row.description,
        created_at=row.created_at,
    )


@images_router.put("/{image_id}/content")
@handle_errors
async def replace_image_content(image_id: str, file: UploadFile):
    """Replace the image file with a new upload.

    Args:
        image_id: The image UUID.
        file: New image file.

    Returns:
        Updated image metadata.
    """
    row = await image_service.replace_image_content(image_id, file)

    return GetImageResponse(
        id=row.id,
        filename=row.filename,
        content_type=row.content_type,
        file_size_bytes=row.file_size_bytes,
        description=row.description,
        created_at=row.created_at,
    )


@images_router.delete("/{image_id}")
@handle_errors
async def delete_image(image_id: str):
    """Delete an image.

    Args:
        image_id: The image UUID.

    Returns:
        204 No Content.
    """
    await image_service.delete_image(image_id)

    return Response(status_code=status.HTTP_204_NO_CONTENT)
