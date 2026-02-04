"""Router for document CRUD operations."""

import logging

from fastapi import APIRouter, HTTPException, Response, UploadFile, status
from fastapi.responses import JSONResponse

from delpro_backend.db.document_service import DocumentService
from delpro_backend.models.v1.document_models import (
    DocumentListItem,
    GetDocumentResponse,
    UploadedDocument,
)
from delpro_backend.services.rag_service import RAGService
from delpro_backend.utils.handle_errors import handle_errors
from delpro_backend.utils.settings import settings

logger = logging.getLogger(__name__)

documents_router = APIRouter(prefix="/documents", tags=["documents"])

# Constants
ALLOWED_FILE_TYPES = ["application/pdf", "text/plain"]
MAX_FILES_PER_UPLOAD = 5


@documents_router.get("/test")
async def test_endpoint():
    """Simple test endpoint to verify router is loaded."""
    return {"message": "Documents router is working!"}


@documents_router.post("")
@handle_errors
async def upload_documents(files: list[UploadFile]):
    """Upload PDF or TXT documents for RAG processing (1-5 files, SYNCHRONOUS).

    Args:
        files: List of uploaded files (PDF or TXT), maximum 5 files

    Returns:
        Upload confirmation with document IDs and status
    """
    # Validate number of files
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files provided",
        )

    if len(files) > MAX_FILES_PER_UPLOAD:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Too many files. Maximum: {MAX_FILES_PER_UPLOAD}",
        )

    # Validate ALL files BEFORE reading them
    for file in files:
        # Validate file type
        content_type = file.content_type or "application/octet-stream"
        if content_type not in ALLOWED_FILE_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file type '{content_type}' for '{file.filename}'. "
                f"Allowed: {', '.join(ALLOWED_FILE_TYPES)}",
            )

    # All files are valid - now read and process them
    uploaded_documents: list[UploadedDocument] = []

    for file in files:
        # Read file
        file_bytes = await file.read()
        file_size_mb = len(file_bytes) / (1024 * 1024)

        # Validate file size
        if file_size_mb > settings.MAX_FILE_SIZE_MB:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File '{file.filename}' too large ({file_size_mb:.2f}MB). "
                f"Maximum: {settings.MAX_FILE_SIZE_MB}MB",
            )

        # Get content type with fallback
        content_type = file.content_type or "application/octet-stream"

        # Create document record
        doc = await DocumentService.create_document(
            filename=file.filename or "untitled",
            content_type=content_type,
            file_bytes=file_bytes,
        )

        # Process document SYNCHRONOUSLY
        chunk_count = await RAGService.process_document(doc.id, file_bytes, content_type)

        uploaded_documents.append(
            UploadedDocument(
                id=doc.id,
                filename=doc.filename,
                file_size_bytes=doc.file_size_bytes,
                status="completed",
                chunk_count=chunk_count,
            )
        )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=[doc.model_dump() for doc in uploaded_documents],
    )


@documents_router.get("")
@handle_errors
async def list_documents():
    """List all uploaded documents with metadata.

    Returns:
        List of documents with chunk counts
    """
    docs_with_counts = await DocumentService.list_documents()

    documents = [
        DocumentListItem(
            id=doc.id,
            filename=doc.filename,
            content_type=doc.content_type,
            file_size_bytes=doc.file_size_bytes,
            upload_date=str(doc.upload_date),
            status=doc.status,
            chunk_count=count,
        ).model_dump()
        for doc, count in docs_with_counts
    ]

    return JSONResponse(status_code=status.HTTP_200_OK, content=documents)


@documents_router.get("/{document_id}")
@handle_errors
async def get_document(document_id: str):
    """Get detailed information about a single document.

    Args:
        document_id: The document ID

    Returns:
        Document details with chunk preview
    """
    doc, chunks = await DocumentService.get_document_with_chunks(document_id)

    # Get first 3 chunks as preview
    chunks_preview = [chunk.content[:400] + "..." for chunk in chunks[:3]]

    return GetDocumentResponse(
        id=doc.id,
        filename=doc.filename,
        content_type=doc.content_type,
        file_size_bytes=doc.file_size_bytes,
        upload_date=doc.upload_date,
        status=doc.status,
        chunk_count=len(chunks),
        chunks_preview=chunks_preview,
    )


@documents_router.delete("/{document_id}")
@handle_errors
async def delete_document(document_id: str):
    """Delete a document and all associated chunks/embeddings.

    Args:
        document_id: The document ID

    Returns:
        Deletion confirmation
    """
    await DocumentService.delete_document(document_id)

    return Response(status_code=status.HTTP_204_NO_CONTENT)
