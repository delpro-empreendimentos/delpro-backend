"""Pydantic models for document endpoints."""

from datetime import datetime

from pydantic import BaseModel, Field


class UploadedDocument(BaseModel):
    """Single uploaded document result."""

    id: str
    filename: str
    file_size_bytes: int
    status: str
    chunk_count: int


class UploadDocumentsResponse(BaseModel):
    """Response after uploading documents (1-5 files)."""

    documents: list[UploadedDocument]


class DocumentListItem(BaseModel):
    """Single document item in list response."""

    id: str
    filename: str
    content_type: str
    file_size_bytes: int
    upload_date: str
    status: str
    chunk_count: int


class GetDocumentsResponse(BaseModel):
    """Response for GET /documents - listing all documents."""

    documents: list[DocumentListItem]
    total: int


class GetDocumentResponse(BaseModel):
    """Response for GET /documents/{id} - detailed document info."""

    id: str
    filename: str
    content_type: str
    file_size_bytes: int
    upload_date: datetime
    status: str
    chunk_count: int
    chunks_preview: list[str] = Field(max_length=3)


class UpdateDocumentContentRequest(BaseModel):
    """Request body for PUT /documents/{id}/content."""

    content: str = Field(min_length=1)


class UpdateDocumentMetadataRequest(BaseModel):
    """Request body for PUT /documents/{id}."""

    filename: str | None = Field(default=None, min_length=1, max_length=255)


class DeleteDocumentResponse(BaseModel):
    """Response after deleting a document."""

    id: str
    message: str
