"""Router for document CRUD operations."""

from fastapi import APIRouter, Response, UploadFile, status
from fastapi.responses import JSONResponse

from delpro_backend.models.v1.document_models import (
    DocumentListItem,
    GetDocumentResponse,
)
from delpro_backend.services.document_service import DocumentService
from delpro_backend.services.rag_service import RAGService
from delpro_backend.services.vector_service import VectorService
from delpro_backend.utils.builders import get_embeddings
from delpro_backend.utils.handle_errors import handle_errors
from delpro_backend.utils.logger import get_logger

logger_extra = {"component.name": "DocumentRouter", "component.version": "v1"}
logger = get_logger(__name__)

documents_router = APIRouter(prefix="/documents", tags=["documents"])

# Initialize services with dependency injection
_embeddings = get_embeddings()
_vector_service = VectorService(embeddings=_embeddings)
_rag_service = RAGService(vector_service=_vector_service, embeddings=_embeddings)
document_service = DocumentService(rag_service=_rag_service)


@documents_router.post("")
@handle_errors
async def upload_documents(files: list[UploadFile]):
    """Upload PDF or TXT documents for RAG processing (1-5 files, SYNCHRONOUS).

    Args:
        files: List of uploaded files (PDF or TXT), maximum 5 files

    Returns:
        Upload confirmation with document IDs and status
    """
    documents = await document_service.create_document(files)

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=[doc.model_dump() for doc in documents],
    )


@documents_router.get("")
@handle_errors
async def list_documents():
    """List all uploaded documents with metadata.

    Returns:
        List of documents with chunk counts
    """
    docs_with_counts = await document_service.list_documents()

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
    doc, chunks = await document_service.get_document_with_chunks(document_id)

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
    await document_service.delete_document(document_id)

    return Response(status_code=status.HTTP_204_NO_CONTENT)
