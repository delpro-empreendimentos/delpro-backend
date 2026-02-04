"""Service for vector operations on document chunks."""

import logging
from uuid import uuid4

from sqlalchemy import func, insert, select, text

from delpro_backend.db.db_service import AsyncSessionFactory
from delpro_backend.db.models import ChunkRow
from delpro_backend.utils.embeddings_builder import get_embeddings

logger = logging.getLogger(__name__)


class VectorService:
    """Database service for vector operations (static methods)."""

    @staticmethod
    async def save_chunks_with_embeddings(
        document_id: str,
        chunks: list[dict],  # {"content": str, "metadata": dict, "chunk_index": int}
    ) -> int:
        """Save chunks with generated embeddings.

        Args:
            document_id: The parent document ID
            chunks: List of chunk dictionaries with content, metadata, and index

        Returns:
            Number of chunks saved
        """
        async with AsyncSessionFactory() as session:
            embeddings_model = get_embeddings()

            # Generate embeddings in batch
            contents = [chunk["content"] for chunk in chunks]
            embeddings = await embeddings_model.aembed_documents(contents)

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
            logger.info(f"Saved {len(chunks)} chunks for document {document_id}")

        return len(chunks)

    @staticmethod
    async def semantic_search(
        query_embedding: list[float],
        top_k: int = 3,
    ) -> list[tuple[ChunkRow, float]]:
        """Perform semantic search using cosine similarity.

        Args:
            query_embedding: The query embedding vector
            top_k: Number of results to return

        Returns:
            List of (ChunkRow, similarity_score) tuples, ordered by relevance
        """
        async with AsyncSessionFactory() as session:
            stmt = (
                select(
                    ChunkRow,
                    (1 - ChunkRow.embedding.cosine_distance(query_embedding)).label("similarity"),
                )
                .order_by(text("similarity DESC"))
                .limit(top_k)
            )
            result = await session.execute(stmt)
            rows = result.all()

        return [(row[0], row[1]) for row in rows]

