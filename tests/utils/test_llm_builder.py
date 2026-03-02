"""Tests for the builders module (get_llm, get_embeddings)."""

import os
import threading
import time
import unittest
from unittest.mock import MagicMock, patch

from langchain_google_genai import ChatGoogleGenerativeAI

import delpro_backend.utils.builders as builders_module
from tests.keys_test import DEFAULT_KEYS

for key, value in DEFAULT_KEYS.items():
    os.environ.setdefault(key, value)


class TestGetLLM(unittest.TestCase):
    """Tests for get_llm function."""

    def setUp(self):
        """Reset the singleton before each test."""
        builders_module._llm = None

    @patch("delpro_backend.utils.builders.ChatGoogleGenerativeAI")
    def test_creates_llm_on_first_call(self, mock_chat_google):
        """Test that get_llm creates a new LLM instance on first call."""
        mock_instance = MagicMock(spec=ChatGoogleGenerativeAI)
        mock_chat_google.return_value = mock_instance

        result = builders_module.get_llm()

        mock_chat_google.assert_called_once()
        self.assertEqual(result, mock_instance)

    @patch("delpro_backend.utils.builders.ChatGoogleGenerativeAI")
    def test_returns_cached_llm_on_subsequent_calls(self, mock_chat_google):
        """Test that get_llm returns cached instance on subsequent calls."""
        mock_instance = MagicMock(spec=ChatGoogleGenerativeAI)
        mock_chat_google.return_value = mock_instance

        result1 = builders_module.get_llm()
        result2 = builders_module.get_llm()

        mock_chat_google.assert_called_once()
        self.assertIs(result1, result2)

    @patch("delpro_backend.utils.builders.ChatGoogleGenerativeAI")
    def test_uses_correct_settings(self, mock_chat_google):
        """Test that get_llm uses correct settings from environment."""
        mock_instance = MagicMock(spec=ChatGoogleGenerativeAI)
        mock_chat_google.return_value = mock_instance

        builders_module.get_llm()

        call_kwargs = mock_chat_google.call_args[1]
        self.assertEqual(call_kwargs["model"], "gemini-2.5-flash")
        self.assertEqual(call_kwargs["api_key"], "test")
        self.assertEqual(call_kwargs["temperature"], 0)
        self.assertEqual(call_kwargs["max_tokens"], 1024)

    @patch("delpro_backend.utils.builders.ChatGoogleGenerativeAI")
    def test_thread_safe_singleton(self, mock_chat_google):
        """Test that get_llm is thread-safe and only creates one instance."""
        mock_instance = MagicMock(spec=ChatGoogleGenerativeAI)

        def create_with_delay(*args, **kwargs):
            time.sleep(0.01)
            return mock_instance

        mock_chat_google.side_effect = create_with_delay

        results = []

        def call_get_llm():
            results.append(builders_module.get_llm())

        threads = [threading.Thread(target=call_get_llm) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(mock_chat_google.call_count, 1)
        for result in results:
            self.assertIs(result, mock_instance)


class TestGetEmbeddings(unittest.TestCase):
    """Tests for get_embeddings function."""

    def setUp(self):
        """Reset the singleton before each test."""
        builders_module._embeddings = None

    @patch("delpro_backend.utils.builders.GoogleGenerativeAIEmbeddings")
    def test_creates_embeddings_on_first_call(self, mock_embeddings_cls):
        """Test that get_embeddings creates a new instance on first call."""
        mock_instance = MagicMock()
        mock_embeddings_cls.return_value = mock_instance

        result = builders_module.get_embeddings()

        mock_embeddings_cls.assert_called_once()
        self.assertEqual(result, mock_instance)

    @patch("delpro_backend.utils.builders.GoogleGenerativeAIEmbeddings")
    def test_returns_cached_embeddings_on_subsequent_calls(self, mock_embeddings_cls):
        """Test that get_embeddings returns cached instance on subsequent calls."""
        mock_instance = MagicMock()
        mock_embeddings_cls.return_value = mock_instance

        result1 = builders_module.get_embeddings()
        result2 = builders_module.get_embeddings()

        mock_embeddings_cls.assert_called_once()
        self.assertIs(result1, result2)

    @patch("delpro_backend.utils.builders.GoogleGenerativeAIEmbeddings")
    def test_thread_safe_embeddings_singleton(self, mock_embeddings_cls):
        """Test that get_embeddings is thread-safe and only creates one instance."""
        mock_instance = MagicMock()

        def create_with_delay(*args, **kwargs):
            time.sleep(0.01)
            return mock_instance

        mock_embeddings_cls.side_effect = create_with_delay

        results = []

        def call_get_embeddings():
            results.append(builders_module.get_embeddings())

        threads = [threading.Thread(target=call_get_embeddings) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(mock_embeddings_cls.call_count, 1)
        for result in results:
            self.assertIs(result, mock_instance)
