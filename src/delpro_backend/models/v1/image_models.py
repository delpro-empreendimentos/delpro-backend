"""Pydantic models for image endpoints."""

from datetime import datetime

from pydantic import BaseModel, Field


class UploadedImage(BaseModel):
    """Response after uploading an image."""

    id: str
    filename: str
    file_size_bytes: int
    description: str


class ImageListItem(BaseModel):
    """Single image item in list response."""

    id: str
    filename: str
    content_type: str
    file_size_bytes: int
    description: str
    created_at: datetime


class GetImageResponse(BaseModel):
    """Response for GET /images/{id}."""

    id: str
    filename: str
    content_type: str
    file_size_bytes: int
    description: str
    created_at: datetime


class UpdateImageRequest(BaseModel):
    """Request body for PUT /images/{id}."""

    description: str | None = Field(default=None, min_length=1)
    filename: str | None = Field(default=None, min_length=1, max_length=255)
