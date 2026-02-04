"""RAG service for document processing and retrieval."""

import logging
from io import BytesIO

from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

from delpro_backend.db.document_service import DocumentService
from delpro_backend.db.exceptions import DocumentProcessingError
from delpro_backend.db.vector_service import VectorService
from delpro_backend.utils.embeddings_builder import get_embeddings
from delpro_backend.utils.settings import settings

logger = logging.getLogger(__name__)


class RAGService:
    """Service for RAG orchestration."""

    _splitter: RecursiveCharacterTextSplitter | None = None

    @classmethod
    def _get_text_splitter(cls) -> RecursiveCharacterTextSplitter:
        """Get or create cached text splitter.

        Returns:
            Configured text splitter instance
        """
        if cls._splitter is None:
            cls._splitter = RecursiveCharacterTextSplitter(
                chunk_size=settings.CHUNK_SIZE,
                chunk_overlap=settings.CHUNK_OVERLAP,
                length_function=len,
                separators=["\n\n", "\n", ". ", " ", ""],
            )
        return cls._splitter

    @staticmethod
    async def extract_text_from_pdf(file_bytes: bytes) -> str:
        """Extract text from PDF file.

        Args:
            file_bytes: PDF file content

        Returns:
            Extracted text
        """
        reader = PdfReader(BytesIO(file_bytes))
        text_parts = []
        for page in reader.pages:
            text_parts.append(page.extract_text())
        return "\n\n".join(text_parts)

    @staticmethod
    async def extract_text_from_txt(file_bytes: bytes) -> str:
        """Extract text from TXT file.

        Args:
            file_bytes: TXT file content

        Returns:
            Decoded text
        """
        return file_bytes.decode("utf-8", errors="replace")

    @staticmethod
    async def chunk_text(text: str) -> list[dict]:
        """Split text into chunks with metadata.

        Args:
            text: Text to chunk

        Returns:
            List of chunk dictionaries with content, metadata, and index
        """
        splitter = RAGService._get_text_splitter()
        chunks = splitter.split_text(text)

        return [
            {
                "content": chunk,
                "chunk_index": i,
                "metadata": {"char_count": len(chunk), "position": i},
            }
            for i, chunk in enumerate(chunks)
        ]

    @staticmethod
    async def process_document(
        document_id: str, file_bytes: bytes, content_type: str
    ) -> int:
        """Process document SYNCHRONOUSLY (extract, chunk, embed, store).

        Args:
            document_id: The document ID
            file_bytes: File content
            content_type: MIME type

        Returns:
            Number of chunks created

        Raises:
            DocumentProcessingError: If processing fails
        """
        try:
            # Extract text
            if content_type == "application/pdf":
                text = await RAGService.extract_text_from_pdf(file_bytes)
            elif content_type == "text/plain":
                text = await RAGService.extract_text_from_txt(file_bytes)
            else:
                raise ValueError(f"Unsupported content type: {content_type}")

            # Chunk text
            chunks = await RAGService.chunk_text(text)

            # Save chunks with embeddings
            chunk_count = await VectorService.save_chunks_with_embeddings(
                document_id, chunks
            )

            # Update status to completed
            await DocumentService.update_document_status(document_id, "completed")

            logger.info(f"Processed document {document_id} ({chunk_count} chunks)")
            return chunk_count

        except Exception as e:
            logger.exception(f"Failed to process document {document_id}: {str(e)}")
            await DocumentService.update_document_status(document_id, "failed")
            raise DocumentProcessingError(document_id, str(e)) from e


    @staticmethod
    async def retrieve_context(query: str, top_k: int | None = None) -> dict:
        """Retrieve RAG context using semantic search only.

        Args:
            query: User query
            top_k: Number of chunks to retrieve (defaults to RAG_TOP_K)

        Returns:
            Dictionary with context, sources, and chunk_count
        """
        if not settings.ENABLE_RAG:
            return {"context": "", "sources": [], "chunk_count": 0}

        if top_k is None:
            top_k = settings.RAG_TOP_K

        # Generate query embedding
        embeddings_model = get_embeddings()
        query_embedding = await embeddings_model.aembed_query(query)

        # Semantic search only (no BM25, no RRF)
        results = await VectorService.semantic_search(query_embedding, top_k=top_k)

        if not results:
            return {"context": "", "sources": [], "chunk_count": 0}

        # Extract content from results
        context = "\n\n---\n\n".join([chunk.content for chunk, _ in results])

        return {
            "context": context,
            "sources": [],
            "chunk_count": len(results),
        }
