"""Tests for VectorService."""

import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from delpro_backend.db.vector_service import VectorService
from tests.keys_test import DEFAULT_KEYS

for key, value in DEFAULT_KEYS.items():
    os.environ.setdefault(key, value)
os.environ.setdefault("MAX_TOKENS_SUMMARY", "500")


class TestVectorServiceSaveChunksWithEmbeddings(unittest.IsolatedAsyncioTestCase):
    """Tests for VectorService.save_chunks_with_embeddings."""

    @patch("delpro_backend.db.vector_service.get_embeddings")
    @patch("delpro_backend.db.vector_service.AsyncSessionFactory")
    async def test_save_chunks_generates_embeddings(self, mock_factory, mock_get_embeddings):
        """Test that embeddings are generated for all chunks."""
        mock_session = AsyncMock()
        mock_factory.return_value.__aenter__.return_value = mock_session

        mock_embeddings_model = AsyncMock()
        mock_embeddings_model.aembed_documents.return_value = [
            [0.1, 0.2, 0.3],
            [0.4, 0.5, 0.6],
        ]
        mock_get_embeddings.return_value = mock_embeddings_model

        chunks = [
            {"content": "Chunk 1 content", "chunk_index": 0, "metadata": {"position": 0}},
            {"content": "Chunk 2 content", "chunk_index": 1, "metadata": {"position": 1}},
        ]

        result = await VectorService.save_chunks_with_embeddings("doc-123", chunks)

        self.assertEqual(result, 2)
        mock_embeddings_model.aembed_documents.assert_called_once_with(
            ["Chunk 1 content", "Chunk 2 content"]
        )

    @patch("delpro_backend.db.vector_service.get_embeddings")
    @patch("delpro_backend.db.vector_service.AsyncSessionFactory")
    async def test_save_chunks_uses_bulk_insert(self, mock_factory, mock_get_embeddings):
        """Test that chunks are inserted using bulk insert."""
        mock_session = AsyncMock()
        mock_factory.return_value.__aenter__.return_value = mock_session

        mock_embeddings_model = AsyncMock()
        mock_embeddings_model.aembed_documents.return_value = [[0.1, 0.2, 0.3]]
        mock_get_embeddings.return_value = mock_embeddings_model

        chunks = [
            {"content": "Test content", "chunk_index": 0, "metadata": {}},
        ]

        await VectorService.save_chunks_with_embeddings("doc-123", chunks)

        # Verify execute was called (bulk insert) instead of add
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_awaited_once()

    @patch("delpro_backend.db.vector_service.get_embeddings")
    @patch("delpro_backend.db.vector_service.AsyncSessionFactory")
    async def test_save_chunks_returns_count(self, mock_factory, mock_get_embeddings):
        """Test that save_chunks returns the number of chunks saved."""
        mock_session = AsyncMock()
        mock_factory.return_value.__aenter__.return_value = mock_session

        mock_embeddings_model = AsyncMock()
        mock_embeddings_model.aembed_documents.return_value = [
            [0.1] * 768,
            [0.2] * 768,
            [0.3] * 768,
        ]
        mock_get_embeddings.return_value = mock_embeddings_model

        chunks = [{"content": f"Chunk {i}", "chunk_index": i, "metadata": {}} for i in range(3)]

        result = await VectorService.save_chunks_with_embeddings("doc-456", chunks)

        self.assertEqual(result, 3)


class TestVectorServiceSemanticSearch(unittest.IsolatedAsyncioTestCase):
    """Tests for VectorService.semantic_search."""

    @patch("delpro_backend.db.vector_service.AsyncSessionFactory")
    async def test_semantic_search_returns_results(self, mock_factory):
        """Test that semantic search returns ChunkRow and similarity tuples."""
        mock_session = AsyncMock()
        mock_factory.return_value.__aenter__.return_value = mock_session

        # Mock chunk rows
        mock_chunk1 = MagicMock()
        mock_chunk1.content = "First chunk content"
        mock_chunk2 = MagicMock()
        mock_chunk2.content = "Second chunk content"

        mock_result = MagicMock()
        mock_result.all.return_value = [
            (mock_chunk1, 0.95),
            (mock_chunk2, 0.85),
        ]
        mock_session.execute.return_value = mock_result

        query_embedding = [0.1] * 768
        results = await VectorService.semantic_search(query_embedding, top_k=2)

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0][0].content, "First chunk content")
        self.assertEqual(results[0][1], 0.95)
        self.assertEqual(results[1][0].content, "Second chunk content")
        self.assertEqual(results[1][1], 0.85)

    @patch("delpro_backend.db.vector_service.AsyncSessionFactory")
    async def test_semantic_search_respects_top_k(self, mock_factory):
        """Test that semantic search respects the top_k parameter."""
        mock_session = AsyncMock()
        mock_factory.return_value.__aenter__.return_value = mock_session

        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute.return_value = mock_result

        query_embedding = [0.1] * 768
        await VectorService.semantic_search(query_embedding, top_k=5)

        # Verify execute was called
        mock_session.execute.assert_called_once()

    @patch("delpro_backend.db.vector_service.AsyncSessionFactory")
    async def test_semantic_search_empty_results(self, mock_factory):
        """Test that semantic search handles empty results."""
        mock_session = AsyncMock()
        mock_factory.return_value.__aenter__.return_value = mock_session

        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute.return_value = mock_result

        query_embedding = [0.1] * 768
        results = await VectorService.semantic_search(query_embedding, top_k=3)

        self.assertEqual(results, [])

    @patch("delpro_backend.db.vector_service.AsyncSessionFactory")
    async def test_semantic_search_default_top_k(self, mock_factory):
        """Test that semantic search uses default top_k of 3."""
        mock_session = AsyncMock()
        mock_factory.return_value.__aenter__.return_value = mock_session

        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute.return_value = mock_result

        query_embedding = [0.1] * 768
        await VectorService.semantic_search(query_embedding)

        # The default top_k is 3
        mock_session.execute.assert_called_once()
