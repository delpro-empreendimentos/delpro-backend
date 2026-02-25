"""Service for document CRUD operations."""

from collections.abc import Sequence
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy import func, select

from delpro_backend.db.db_service import AsyncSessionFactory
from delpro_backend.models.v1.database_models import ChunkRow, DocumentRow
from delpro_backend.models.v1.document_models import UpdateDocumentMetadataRequest, UploadedDocument
from delpro_backend.models.v1.exception_models import (
    InvalidRequestError,
    MissingParametersRequestError,
    ResourceNotFoundError,
)
from delpro_backend.services.rag_service import RAGService
from delpro_backend.utils.logger import get_logger
from delpro_backend.utils.settings import settings

logger_extra = {"component.name": "DocumentService", "component.version": "v1"}
logger = get_logger(__name__)

# # Constants
# settings.ALLOWED_FILE_TYPES = ["application/pdf", "text/plain"]
# settings.MAX_FILES_PER_UPLOAD = 5


class DocumentService:
    """Service for document CRUD operations."""

    def __init__(self, rag_service: RAGService):
        """Initialize DocumentService with dependencies.

        Args:
            rag_service: Service for RAG processing
        """
        self._rag_service = rag_service

    async def create_document(
        self,
        files: list[UploadFile],
    ) -> list[UploadedDocument]:
        """Create document records from uploaded files.

        Args:
            files: List of uploaded files (PDF or TXT)

        Returns:
            List of UploadedDocument with processing status
        """
        # Validate number of files
        if not files:
            raise MissingParametersRequestError()

        if len(files) > settings.MAX_FILES_PER_UPLOAD:
            raise InvalidRequestError("Request contain more files than accepted.")

        # Validate ALL file types BEFORE reading them
        if any(
            (f.content_type or "application/octet-stream") not in settings.ALLOWED_FILE_TYPES
            for f in files
        ):
            raise InvalidRequestError("All files must be '.txt' or '.pdf' types.")

        # All files are valid - now read and process them
        uploaded_documents: list[UploadedDocument] = []

        for file in files:
            # Read file
            file_bytes = await file.read()
            file_size_mb = len(file_bytes) / (1024 * 1024)

            # Validate file size
            if file_size_mb > settings.MAX_FILE_SIZE_MB:
                raise InvalidRequestError(
                    f"File '{file.filename}' too large ({file_size_mb:.2f}MB). "
                    f"Maximum: {settings.MAX_FILE_SIZE_MB}MB"
                )

            content_type = file.content_type or "application/octet-stream"

            # Create document record

            async with AsyncSessionFactory() as session:
                doc = DocumentRow(
                    id=str(uuid4()),
                    filename=file.filename or "untitled",
                    content_type=content_type,
                    file_size_bytes=len(file_bytes),
                    file_content=file_bytes,
                    status="processing",
                )
                session.add(doc)
                await session.commit()
                await session.refresh(doc)

            # Process document
            chunk_count = await self._rag_service.process_document(doc.id, file_bytes, content_type)

            uploaded_documents.append(
                UploadedDocument(
                    id=doc.id,
                    filename=doc.filename,
                    file_size_bytes=doc.file_size_bytes,
                    status="completed",
                    chunk_count=chunk_count,
                )
            )

        return uploaded_documents

    async def update_document_status(self, document_id: str, new_status: str) -> None:
        """Update document processing status.

        Args:
            document_id: The document ID
            new_status: New status (processing, completed, failed)

        Raises:
            ResourceNotFoundError: If document not found
        """
        async with AsyncSessionFactory() as session:
            doc = await session.get(DocumentRow, document_id)
            if not doc:
                logger.error(f"Document not found {document_id}", extra=logger_extra)
                raise ResourceNotFoundError("Document", document_id)

            doc.status = new_status
            await session.commit()

    async def get_document(self, document_id: str) -> DocumentRow:
        """Retrieve a document by ID.

        Args:
            document_id: The document ID

        Returns:
            DocumentRow

        Raises:
            ResourceNotFoundError: If document not found
        """
        async with AsyncSessionFactory() as session:
            doc = await session.get(DocumentRow, document_id)

        if not doc:
            logger.error(f"Document not found {document_id}", extra=logger_extra)
            raise ResourceNotFoundError("Document", document_id)

        return doc

    async def list_documents(self) -> list[tuple[DocumentRow, int]]:
        """List all documents with chunk counts.

        Returns:
            List of (DocumentRow, chunk_count) tuples
        """
        try:
            async with AsyncSessionFactory() as session:
                stmt = (
                    select(DocumentRow, func.count(ChunkRow.id).label("chunk_count"))
                    .outerjoin(ChunkRow, DocumentRow.id == ChunkRow.document_id)
                    .group_by(DocumentRow.id)
                    .order_by(DocumentRow.upload_date.desc())
                )
                result = await session.execute(stmt)
                rows = result.all()

            return [(row[0], row[1]) for row in rows]
        except Exception as e:
            logger.error("An error ocurred while listing documents: %s", e, extra=logger_extra)
            raise e

    async def get_document_with_chunks(
        self,
        document_id: str,
    ) -> tuple[DocumentRow, Sequence[ChunkRow]]:
        """Get document with all its chunks.

        Args:
            document_id: The document ID

        Returns:
            Tuple of (DocumentRow, list[ChunkRow])

        Raises:
            ResourceNotFoundError: If document not found
        """
        async with AsyncSessionFactory() as session:
            doc = await session.get(DocumentRow, document_id)
            if not doc:
                logger.error(f"Document not found {document_id}", extra=logger_extra)
                raise ResourceNotFoundError("Document", document_id)

            stmt = (
                select(ChunkRow)
                .where(ChunkRow.document_id == document_id)
                .order_by(ChunkRow.chunk_index.asc())
            )
            result = await session.execute(stmt)
            chunks = result.scalars().all()

        return (doc, chunks)

    async def get_document_content(self, document_id: str) -> tuple[bytes, str, str]:
        """Retrieve raw document bytes for download/preview.

        Args:
            document_id: The document ID

        Returns:
            Tuple of (file_bytes, content_type, filename).

        Raises:
            ResourceNotFoundError: If document not found.
        """
        doc = await self.get_document(document_id)
        return doc.file_content, doc.content_type, doc.filename

    async def update_document_content(self, document_id: str, new_content: bytes) -> DocumentRow:
        """Replace the raw file content of a text document and re-process chunks.

        Args:
            document_id: The document ID
            new_content: New file content as bytes

        Returns:
            Updated DocumentRow

        Raises:
            ResourceNotFoundError: If document not found.
            InvalidRequestError: If document is not text/plain.
        """
        async with AsyncSessionFactory() as session:
            doc = await session.get(DocumentRow, document_id)
            if not doc:
                logger.error(f"Document not found {document_id}", extra=logger_extra)
                raise ResourceNotFoundError("Document", document_id)

            if doc.content_type != "text/plain":
                raise InvalidRequestError("Only text/plain documents can be edited.")

            doc.file_content = new_content
            doc.file_size_bytes = len(new_content)

            # Delete existing chunks for this document
            stmt = select(ChunkRow).where(ChunkRow.document_id == document_id)
            result = await session.execute(stmt)
            for chunk in result.scalars().all():
                await session.delete(chunk)

            await session.commit()
            await session.refresh(doc)

        # Re-process the document with new content
        await self._rag_service.process_document(document_id, new_content, "text/plain")

        # Update status to completed
        await self.update_document_status(document_id, "completed")

        logger.info(f"Updated document content {document_id}", extra=logger_extra)
        return doc

    async def update_document_metadata(
        self,
        document_id: str,
        data: UpdateDocumentMetadataRequest,
    ) -> DocumentRow:
        """Update document metadata (filename).

        Args:
            document_id: The document ID
            data: Fields to update

        Returns:
            Updated DocumentRow

        Raises:
            ResourceNotFoundError: If document not found.
        """
        async with AsyncSessionFactory() as session:
            doc = await session.get(DocumentRow, document_id)
            if not doc:
                logger.error(f"Document not found {document_id}", extra=logger_extra)
                raise ResourceNotFoundError("Document", document_id)

            if data.filename is not None:
                doc.filename = data.filename

            await session.commit()
            await session.refresh(doc)

        logger.info(f"Updated document metadata {document_id}", extra=logger_extra)
        return doc

    async def delete_document(self, document_id: str) -> None:
        """Delete a document and all its chunks (CASCADE).

        Args:
            document_id: The document ID

        Raises:
            ResourceNotFoundError: If document not found
        """
        async with AsyncSessionFactory() as session:
            doc = await session.get(DocumentRow, document_id)
            if not doc:
                logger.error(f"Document not found {document_id}", extra=logger_extra)
                raise ResourceNotFoundError("Document", document_id)

            await session.delete(doc)
            await session.commit()

        logger.info(f"Deleted document {document_id}", extra=logger_extra)
