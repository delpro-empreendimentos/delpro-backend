"""Tests for the embeddings builder module."""

import os
import threading
import time
import unittest
from unittest.mock import MagicMock, patch

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test_db")
os.environ.setdefault("WPP_PHONE_ID", "test")
os.environ.setdefault("WPP_TEST_NUMER", "test")
os.environ.setdefault("WPP_TOKEN", "test")
os.environ.setdefault("API_KEY", "test")
os.environ.setdefault("PROJECT_ID", "test")
os.environ.setdefault("GEMINI_MODEL", "gemini-2.0-flash")
os.environ.setdefault("MAX_TOKENS", "1024")
os.environ.setdefault("LLM_TEMPERATURE", "0")
os.environ.setdefault("MAX_HISTORY_MESSAGES", "20")
os.environ.setdefault("MAX_TOKENS_SUMMARY", "500")

from langchain_google_genai import GoogleGenerativeAIEmbeddings

import delpro_backend.utils.embeddings_builder as embeddings_builder_module


class TestGetEmbeddings(unittest.TestCase):
    """Tests for get_embeddings function."""

    def setUp(self):
        """Reset the singleton before each test."""
        embeddings_builder_module._embeddings = None

    @patch("delpro_backend.utils.embeddings_builder.GoogleGenerativeAIEmbeddings")
    def test_creates_embeddings_on_first_call(self, mock_embeddings_class):
        """Test that get_embeddings creates a new instance on first call."""
        mock_instance = MagicMock(spec=GoogleGenerativeAIEmbeddings)
        mock_embeddings_class.return_value = mock_instance

        result = embeddings_builder_module.get_embeddings()

        mock_embeddings_class.assert_called_once()
        self.assertEqual(result, mock_instance)

    @patch("delpro_backend.utils.embeddings_builder.GoogleGenerativeAIEmbeddings")
    def test_returns_cached_embeddings_on_subsequent_calls(self, mock_embeddings_class):
        """Test that get_embeddings returns cached instance on subsequent calls."""
        mock_instance = MagicMock(spec=GoogleGenerativeAIEmbeddings)
        mock_embeddings_class.return_value = mock_instance

        result1 = embeddings_builder_module.get_embeddings()
        result2 = embeddings_builder_module.get_embeddings()

        # Should only create once
        mock_embeddings_class.assert_called_once()
        self.assertIs(result1, result2)

    @patch("delpro_backend.utils.embeddings_builder.GoogleGenerativeAIEmbeddings")
    @patch("delpro_backend.utils.embeddings_builder.settings")
    def test_uses_correct_settings(self, mock_settings, mock_embeddings_class):
        """Test that get_embeddings uses correct settings."""
        mock_settings.EMBEDDING_MODEL = "models/text-embedding-004"
        mock_settings.API_KEY = "test-api-key"

        mock_instance = MagicMock(spec=GoogleGenerativeAIEmbeddings)
        mock_embeddings_class.return_value = mock_instance

        embeddings_builder_module.get_embeddings()

        call_kwargs = mock_embeddings_class.call_args[1]
        self.assertEqual(call_kwargs["model"], "models/text-embedding-004")
        self.assertEqual(call_kwargs["api_key"], "test-api-key")

    @patch("delpro_backend.utils.embeddings_builder.GoogleGenerativeAIEmbeddings")
    def test_thread_safe_singleton(self, mock_embeddings_class):
        """Test that get_embeddings is thread-safe and only creates one instance."""
        mock_instance = MagicMock(spec=GoogleGenerativeAIEmbeddings)

        def create_with_delay(*args, **kwargs):
            time.sleep(0.01)
            return mock_instance

        mock_embeddings_class.side_effect = create_with_delay

        results = []

        def call_get_embeddings():
            results.append(embeddings_builder_module.get_embeddings())

        threads = [threading.Thread(target=call_get_embeddings) for _ in range(5)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # Should only create once despite concurrent access
        self.assertEqual(mock_embeddings_class.call_count, 1)

        # All threads should get the same instance
        for result in results:
            self.assertIs(result, mock_instance)
