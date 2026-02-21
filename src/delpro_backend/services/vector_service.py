"""Service for vector operations on document chunks."""

from uuid import uuid4

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from sqlalchemy import insert, select

from delpro_backend.db.db_service import AsyncSessionFactory
from delpro_backend.models.v1.database_models import ChunkRow
from delpro_backend.utils.logger import get_logger

logger_extra = {"component.name": "VectorService", "component.version": "v1"}
logger = get_logger(__name__)


class VectorService:
    """Service for vector operations on document chunks."""

    def __init__(self, embeddings: GoogleGenerativeAIEmbeddings):
        """Initialize VectorService with embeddings model.

        Args:
            embeddings: Embeddings model for generating vectors
        """
        self._embeddings = embeddings

    async def save_chunks_with_embeddings(
        self,
        document_id: str,
        chunks: list[dict],
    ) -> int:
        """Save chunks with generated embeddings.

        Args:
            document_id: The parent document ID
            chunks: List of chunk dictionaries with content, metadata, and index

        Returns:
            Number of chunks saved
        """
        async with AsyncSessionFactory() as session:
            # Generate embeddings in batch
            contents = [chunk["content"] for chunk in chunks]
            embeddings = await self._embeddings.aembed_documents(contents)

            # Prepare bulk data
            chunk_rows_data = [
                {
                    "id": str(uuid4()),
                    "document_id": document_id,
                    "chunk_index": chunk["chunk_index"],
                    "content": chunk["content"],
                    "embedding": embeddings[i],
                    "chunk_metadata": chunk["metadata"],
                }
                for i, chunk in enumerate(chunks)
            ]

            # Bulk insert (single SQL statement)
            stmt = insert(ChunkRow).values(chunk_rows_data)
            await session.execute(stmt)
            await session.commit()
            logger.info(
                f"Saved {len(chunks)} chunks for document {document_id}", extra=logger_extra
            )

        return len(chunks)

    async def semantic_search(self, query_embedding: list[float]) -> str | None:
        """Return the most similar chunk content using cosine distance.

        Args:
            query_embedding: The query embedding vector.

        Returns:
            The content of the most similar chunk, or None if no chunks exist.
        """
        async with AsyncSessionFactory() as session:
            stmt = (
                select(ChunkRow.content)
                .order_by(ChunkRow.embedding.cosine_distance(query_embedding))
                .limit(1)
            )
            return await session.scalar(stmt)
