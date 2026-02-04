"""Tests for the embeddings builder module."""

import os
import threading
import time
import unittest
from unittest.mock import MagicMock, patch

from langchain_google_genai import GoogleGenerativeAIEmbeddings

import delpro_backend.utils.embeddings_builder as embeddings_builder_module
from tests.keys_test import DEFAULT_KEYS

for key, value in DEFAULT_KEYS.items():
    os.environ.setdefault(key, value)
os.environ.setdefault("MAX_TOKENS_SUMMARY", "500")


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
