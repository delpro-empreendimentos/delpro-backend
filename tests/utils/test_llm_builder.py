"""Tests for the builders module (get_llm, get_summary_llm)."""

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


class TestGetSummaryLLM(unittest.TestCase):
    """Tests for get_summary_llm function."""

    def setUp(self):
        """Reset the singleton before each test."""
        builders_module._summary_llm = None

    @patch("delpro_backend.utils.builders.ChatGoogleGenerativeAI")
    def test_creates_summary_llm_on_first_call(self, mock_chat_google):
        """Test that get_summary_llm creates a new LLM instance on first call."""
        mock_instance = MagicMock(spec=ChatGoogleGenerativeAI)
        mock_chat_google.return_value = mock_instance

        result = builders_module.get_summary_llm()

        mock_chat_google.assert_called_once()
        self.assertEqual(result, mock_instance)

    @patch("delpro_backend.utils.builders.ChatGoogleGenerativeAI")
    def test_returns_cached_summary_llm_on_subsequent_calls(self, mock_chat_google):
        """Test that get_summary_llm returns cached instance on subsequent calls."""
        mock_instance = MagicMock(spec=ChatGoogleGenerativeAI)
        mock_chat_google.return_value = mock_instance

        result1 = builders_module.get_summary_llm()
        result2 = builders_module.get_summary_llm()

        mock_chat_google.assert_called_once()
        self.assertIs(result1, result2)

    @patch("delpro_backend.utils.builders.ChatGoogleGenerativeAI")
    @patch("delpro_backend.utils.builders.settings")
    def test_uses_max_tokens_summary_setting(self, mock_settings, mock_chat_google):
        """Test that get_summary_llm uses MAX_TOKENS_SUMMARY instead of MAX_TOKENS."""
        mock_settings.GEMINI_MODEL = "gemini-2.0-flash"
        mock_settings.API_KEY = "test-api-key"
        mock_settings.LLM_TEMPERATURE = 0
        mock_settings.MAX_TOKENS_SUMMARY = 2000

        mock_instance = MagicMock(spec=ChatGoogleGenerativeAI)
        mock_chat_google.return_value = mock_instance

        builders_module.get_summary_llm()

        call_kwargs = mock_chat_google.call_args[1]
        self.assertEqual(call_kwargs["max_tokens"], 2000)

    @patch("delpro_backend.utils.builders.ChatGoogleGenerativeAI")
    def test_thread_safe_summary_singleton(self, mock_chat_google):
        """Test that get_summary_llm is thread-safe and only creates one instance."""
        mock_instance = MagicMock(spec=ChatGoogleGenerativeAI)

        def create_with_delay(*args, **kwargs):
            time.sleep(0.01)
            return mock_instance

        mock_chat_google.side_effect = create_with_delay

        results = []

        def call_get_summary_llm():
            results.append(builders_module.get_summary_llm())

        threads = [threading.Thread(target=call_get_summary_llm) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(mock_chat_google.call_count, 1)
        for result in results:
            self.assertIs(result, mock_instance)
