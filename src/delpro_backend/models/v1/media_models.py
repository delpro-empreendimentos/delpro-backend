"""Pydantic models for media endpoints."""

from datetime import datetime

from pydantic import BaseModel, Field


class UploadedMedia(BaseModel):
    """Response after uploading a media file."""

    id: str
    filename: str
    file_size_bytes: int
    description: str


class MediaListItem(BaseModel):
    """Single media item in list response."""

    id: str
    filename: str
    content_type: str
    file_size_bytes: int
    description: str
    created_at: datetime


class GetMediaResponse(BaseModel):
    """Response for GET /media/{id}."""

    id: str
    filename: str
    content_type: str
    file_size_bytes: int
    description: str
    created_at: datetime


class UpdateMediaRequest(BaseModel):
    """Request body for PUT /media/{id}."""

    description: str | None = Field(default=None, min_length=1)
    filename: str | None = Field(default=None, min_length=1, max_length=255)
