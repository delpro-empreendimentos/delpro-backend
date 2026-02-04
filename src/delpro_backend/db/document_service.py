"""Service for document CRUD operations."""

import logging
from collections.abc import Sequence
from uuid import uuid4

from sqlalchemy import func, select

from delpro_backend.db.db_service import AsyncSessionFactory
from delpro_backend.db.exceptions import ResourceNotFoundError
from delpro_backend.db.models import ChunkRow, DocumentRow

logger = logging.getLogger(__name__)


class DocumentService:
    """Database service for document operations (static methods)."""

    @staticmethod
    async def create_document(
        filename: str,
        content_type: str,
        file_bytes: bytes,
    ) -> DocumentRow:
        """Create a new document record with file content.

        Args:
            filename: Original filename
            content_type: MIME type
            file_bytes: File content as bytes

        Returns:
            The created DocumentRow
        """
        async with AsyncSessionFactory() as session:
            doc = DocumentRow(
                id=str(uuid4()),
                filename=filename,
                content_type=content_type,
                file_size_bytes=len(file_bytes),
                file_content=file_bytes,
                status="processing",
            )
            session.add(doc)
            await session.commit()
            await session.refresh(doc)

        return doc

    @staticmethod
    async def update_document_status(document_id: str, status: str) -> None:
        """Update document processing status.

        Args:
            document_id: The document ID
            status: New status (processing, completed, failed)

        Raises:
            ResourceNotFoundError: If document not found
        """
        async with AsyncSessionFactory() as session:
            doc = await session.get(DocumentRow, document_id)
            if not doc:
                raise ResourceNotFoundError("Document", document_id)

            doc.status = status
            await session.commit()

    @staticmethod
    async def get_document(document_id: str) -> DocumentRow:
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
            raise ResourceNotFoundError("Document", document_id)

        return doc

    @staticmethod
    async def list_documents() -> list[tuple[DocumentRow, int]]:
        """List all documents with chunk counts.

        Returns:
            List of (DocumentRow, chunk_count) tuples
        """
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

    @staticmethod
    async def get_document_with_chunks(
        document_id: str,
    ) -> tuple[DocumentRow, Sequence[ChunkRow]]:  # TODO check later the list/sequence
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
                raise ResourceNotFoundError("Document", document_id)

            stmt = (
                select(ChunkRow)
                .where(ChunkRow.document_id == document_id)
                .order_by(ChunkRow.chunk_index.asc())
            )
            result = await session.execute(stmt)
            chunks = result.scalars().all()

        return (doc, chunks)

    @staticmethod
    async def delete_document(document_id: str) -> None:
        """Delete a document and all its chunks (CASCADE).

        Args:
            document_id: The document ID

        Raises:
            ResourceNotFoundError: If document not found
        """
        async with AsyncSessionFactory() as session:
            doc = await session.get(DocumentRow, document_id)
            if not doc:
                raise ResourceNotFoundError("Document", document_id)

            await session.delete(doc)
            await session.commit()

        logger.info(f"Deleted document {document_id}")
