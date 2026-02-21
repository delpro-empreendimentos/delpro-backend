"""RAG service for document processing and retrieval."""

from io import BytesIO

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

from delpro_backend.models.v1.exception_models import DocumentProcessingError
from delpro_backend.services.vector_service import VectorService
from delpro_backend.utils.logger import get_logger
from delpro_backend.utils.settings import settings

logger_extra = {"component.name": "RAGService", "component.version": "v1"}
logger = get_logger(__name__)


class RAGService:
    """Service for RAG orchestration."""

    def __init__(self, vector_service: VectorService, embeddings: GoogleGenerativeAIEmbeddings):
        """Initialize RAGService with dependencies.

        Args:
            vector_service: Service for vector operations
            embeddings: Embeddings model for generating vectors
        """
        self._vector_service = vector_service
        self._embeddings = embeddings
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    def _extract_text_from_pdf(self, file_bytes: bytes) -> str:
        """Extract text from PDF file.

        Args:
            file_bytes: PDF file content

        Returns:
            Extracted text
        """
        reader = PdfReader(BytesIO(file_bytes))
        return "\n\n".join(page.extract_text() for page in reader.pages)

    def _extract_text_from_txt(self, file_bytes: bytes) -> str:
        """Extract text from TXT file.

        Args:
            file_bytes: TXT file content

        Returns:
            Decoded text
        """
        return file_bytes.decode("utf-8", errors="replace")

    def _chunk_text(self, text: str) -> list[dict]:
        """Split text into chunks with metadata.

        Args:
            text: Text to chunk

        Returns:
            List of chunk dictionaries with content, metadata, and index
        """
        chunks = self._splitter.split_text(text)
        return [
            {
                "content": chunk,
                "chunk_index": i,
                "metadata": {"char_count": len(chunk), "position": i},
            }
            for i, chunk in enumerate(chunks)
        ]

    async def process_document(self, document_id: str, file_bytes: bytes, content_type: str) -> int:
        """Process document (extract, chunk, embed, store).

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
            # Extract text based on content type
            if content_type == "application/pdf":
                text = self._extract_text_from_pdf(file_bytes)
            elif content_type == "text/plain":
                text = self._extract_text_from_txt(file_bytes)
            else:
                raise ValueError(f"Unsupported content type: {content_type}")

            # Chunk text
            chunks = self._chunk_text(text)

            # Save chunks with embeddings
            chunk_count = await self._vector_service.save_chunks_with_embeddings(
                document_id, chunks
            )

            logger.info(
                f"Processed document {document_id} ({chunk_count} chunks)", extra=logger_extra
            )
            return chunk_count

        except Exception as e:
            logger.exception(f"Failed to process document {document_id}: {e}", extra=logger_extra)
            raise DocumentProcessingError(document_id, str(e)) from e

    async def retrieve_context(self, query: str):
        """Retrieve RAG context using semantic search.

        Args:
            query: User query
            top_k: Number of chunks to retrieve (defaults to RAG_TOP_K)

        Returns:
            Dictionary with context, sources, and chunk_count
        """
        # Generate query embedding
        query_embedding = await self._embeddings.aembed_query(query)

        # Semantic search
        result = await self._vector_service.semantic_search(query_embedding)

        return result
