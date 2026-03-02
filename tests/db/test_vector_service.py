"""Tests for VectorService."""

import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from delpro_backend.services.vector_service import VectorService
from tests.keys_test import DEFAULT_KEYS

for key, value in DEFAULT_KEYS.items():
    os.environ.setdefault(key, value)


def _make_service():
    mock_embeddings = AsyncMock()
    mock_embeddings.aembed_documents = AsyncMock(return_value=[[0.1, 0.2, 0.3]])
    return VectorService(embeddings=mock_embeddings), mock_embeddings


class TestVectorServiceSaveChunksWithEmbeddings(unittest.IsolatedAsyncioTestCase):
    """Tests for VectorService.save_chunks_with_embeddings."""

    @patch("delpro_backend.services.vector_service.AsyncSessionFactory")
    async def test_save_chunks_returns_count(self, mock_factory):
        """Test that save_chunks returns the number of chunks saved."""
        svc, mock_emb = _make_service()
        mock_emb.aembed_documents.return_value = [[0.1] * 3, [0.2] * 3]

        mock_session = AsyncMock()
        mock_factory.return_value.__aenter__.return_value = mock_session

        chunks = [
            {"content": "Chunk 1", "chunk_index": 0, "metadata": {"position": 0}},
            {"content": "Chunk 2", "chunk_index": 1, "metadata": {"position": 1}},
        ]

        result = await svc.save_chunks_with_embeddings("doc-123", chunks)

        self.assertEqual(result, 2)
        mock_emb.aembed_documents.assert_awaited_once_with(["Chunk 1", "Chunk 2"])

    @patch("delpro_backend.services.vector_service.AsyncSessionFactory")
    async def test_save_chunks_uses_bulk_insert(self, mock_factory):
        """Test that chunks are inserted using bulk execute."""
        svc, _ = _make_service()

        mock_session = AsyncMock()
        mock_factory.return_value.__aenter__.return_value = mock_session

        chunks = [{"content": "Test content", "chunk_index": 0, "metadata": {}}]

        await svc.save_chunks_with_embeddings("doc-123", chunks)

        mock_session.execute.assert_called_once()
        mock_session.commit.assert_awaited_once()


class TestVectorServiceSemanticSearch(unittest.IsolatedAsyncioTestCase):
    """Tests for VectorService.semantic_search."""

    @patch("delpro_backend.services.vector_service.AsyncSessionFactory")
    async def test_semantic_search_returns_result(self, mock_factory):
        """Test that semantic search returns a list of chunk contents."""
        svc, _ = _make_service()

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = ["Found chunk content"]
        mock_session.execute.return_value = mock_result
        mock_factory.return_value.__aenter__.return_value = mock_session

        result = await svc.semantic_search([0.1] * 3072)

        self.assertEqual(result, ["Found chunk content"])

    @patch("delpro_backend.services.vector_service.AsyncSessionFactory")
    async def test_semantic_search_returns_empty_list_when_no_chunks(self, mock_factory):
        """Test that semantic search returns empty list when no chunks exist."""
        svc, _ = _make_service()

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result
        mock_factory.return_value.__aenter__.return_value = mock_session

        result = await svc.semantic_search([0.1] * 3072)

        self.assertEqual(result, [])

    @patch("delpro_backend.services.vector_service.AsyncSessionFactory")
    async def test_semantic_search_calls_execute(self, mock_factory):
        """Test that semantic_search executes the query."""
        svc, _ = _make_service()

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result
        mock_factory.return_value.__aenter__.return_value = mock_session

        await svc.semantic_search([0.5] * 3072)

        mock_session.execute.assert_called_once()

    @patch("delpro_backend.services.vector_service.AsyncSessionFactory")
    async def test_semantic_search_returns_multiple_results(self, mock_factory):
        """Test that semantic search returns multiple chunks when top_k > 1."""
        svc, _ = _make_service()

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = ["Chunk 1", "Chunk 2"]
        mock_session.execute.return_value = mock_result
        mock_factory.return_value.__aenter__.return_value = mock_session

        result = await svc.semantic_search([0.1] * 3072, top_k=2)

        self.assertEqual(result, ["Chunk 1", "Chunk 2"])
