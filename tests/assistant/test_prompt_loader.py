"""Tests for prompt loading and ChatPromptTemplate construction."""

import os
import unittest
from collections.abc import Sequence
from unittest.mock import mock_open, patch

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from delpro_backend.assistant.prompt_loader import (
    build_chat_prompt,
    get_summary_prompt,
    load_prompt_config,
)
from tests.keys_test import DEFAULT_KEYS

for key, value in DEFAULT_KEYS.items():
    os.environ.setdefault(key, value)


class TestLoadPromptConfig(unittest.TestCase):
    """Tests for load_prompt_config."""

    def test_returns_dict(self):
        """Test that load_prompt_config returns a parsed YAML dict."""
        yaml_content = "system_prompt: |\n  You are helpful.\n"
        with patch("builtins.open", mock_open(read_data=yaml_content)):
            config = load_prompt_config()
        self.assertIsInstance(config, dict)
        self.assertIn("system_prompt", config)

    def test_file_not_found(self):
        """Test that FileNotFoundError is raised for missing file."""
        with patch("builtins.open", side_effect=FileNotFoundError):
            with self.assertRaises(FileNotFoundError):
                load_prompt_config("nonexistent.yml")


class TestBuildChatPrompt(unittest.TestCase):
    """Tests for build_chat_prompt."""

    def test_returns_chat_prompt_template(self):
        """Test that build_chat_prompt returns a ChatPromptTemplate."""
        yaml_content = "system_prompt: |\n  You are a sales assistant.\n"
        with patch("builtins.open", mock_open(read_data=yaml_content)):
            prompt = build_chat_prompt()
        self.assertIsInstance(prompt, ChatPromptTemplate)

    def test_template_has_three_messages(self):
        """Test that the template has system, history, and human messages."""
        yaml_content = "system_prompt: |\n  You are a sales assistant.\n"
        with patch("builtins.open", mock_open(read_data=yaml_content)):
            prompt = build_chat_prompt()
        self.assertEqual(len(prompt.messages), 3)

    def test_template_has_messages_placeholder(self):
        """Test that the template includes a MessagesPlaceholder for history."""
        yaml_content = "system_prompt: |\n  You are a sales assistant.\n"
        with patch("builtins.open", mock_open(read_data=yaml_content)):
            prompt = build_chat_prompt()
        history_placeholder = prompt.messages[1]
        self.assertIsInstance(history_placeholder, MessagesPlaceholder)

    def test_default_system_prompt_when_key_missing(self):
        """Test fallback to default system prompt when key is missing."""
        yaml_content = "other_key: value\n"
        with patch("builtins.open", mock_open(read_data=yaml_content)):
            prompt = build_chat_prompt()
        self.assertIsInstance(prompt, ChatPromptTemplate)
        self.assertEqual(len(prompt.messages), 3)


class TestGetSummaryPrompt(unittest.TestCase):
    """Tests for get_summary_prompt."""

    def test_formats_human_message(self):
        """Test that HumanMessage is formatted correctly."""
        yaml_content = "summary_prompt: |\n  Summarize:\n  {conversation}\n"
        messages = [HumanMessage(content="Hello")]

        with patch("builtins.open", mock_open(read_data=yaml_content)):
            result = get_summary_prompt(messages)

        self.assertIn("Cliente: Hello", result)

    # def test_formats_system_message(self):
    #     """Test that HumanMessage is formatted correctly."""
    #     yaml_content = "summary_prompt: |\n  Summarize:\n  {conversation}\n"
    #     messages = [HumanMessage(content="Hello")]

    #     with patch("builtins.open", mock_open(read_data=yaml_content)):
    #         result = get_summary_prompt(messages)

    #     self.assertIn("Cliente: Hello", result)

    def test_formats_ai_message_with_string(self):
        """Test that AIMessage with string content is formatted correctly."""
        yaml_content = "summary_prompt: |\n  Summarize:\n  {conversation}\n"
        messages = [AIMessage(content="Hi there!")]

        with patch("builtins.open", mock_open(read_data=yaml_content)):
            result = get_summary_prompt(messages)

        self.assertIn("Assistente: Hi there!", result)

    def test_formats_ai_message_with_dict_list(self):
        """Test that AIMessage with list of dicts is formatted correctly."""
        yaml_content = "summary_prompt: |\n  Summarize:\n  {conversation}\n"
        messages = [AIMessage(content=[{"type": "text", "text": "Response"}])]

        with patch("builtins.open", mock_open(read_data=yaml_content)):
            result = get_summary_prompt(messages)

        self.assertIn("Assistente: Response", result)

    def test_formats_ai_message_with_string_list(self):
        """Test that AIMessage with list of strings is formatted correctly."""
        yaml_content = "summary_prompt: |\n  Summarize:\n  {conversation}\n"
        messages = [AIMessage(content=["First item"])]

        with patch("builtins.open", mock_open(read_data=yaml_content)):
            result = get_summary_prompt(messages)

        self.assertIn("Assistente: First item", result)

    def test_formats_ai_message_with_empty_list(self):
        """Test that AIMessage with empty list is converted to string."""
        yaml_content = "summary_prompt: |\n  Summarize:\n  {conversation}\n"
        messages = [AIMessage(content=[])]

        with patch("builtins.open", mock_open(read_data=yaml_content)):
            result = get_summary_prompt(messages)

        self.assertIn("Assistente:", result)

    def test_formats_system_message(self):
        """Test that SystemMessage is formatted correctly."""
        yaml_content = "summary_prompt: |\n  Summarize:\n  {conversation}\n"
        messages = [SystemMessage(content="System note")]

        with patch("builtins.open", mock_open(read_data=yaml_content)):
            result = get_summary_prompt(messages)

        self.assertIn("Sistema: System note", result)

    def test_formats_unknown_message(self):
        """Test that SystemMessage is formatted correctly."""
        yaml_content = "summary_prompt: |\n  Summarize:\n  {conversation}\n"
        messages = ["test"]

        with patch("builtins.open", mock_open(read_data=yaml_content)):
            result = get_summary_prompt(messages)  # type: ignore

        self.assertIn("Summarize:\n\n", result)

    def test_formats_multiple_messages(self):
        """Test that multiple messages are formatted correctly."""
        yaml_content = "summary_prompt: |\n  Summarize:\n  {conversation}\n"
        messages = [
            HumanMessage(content="Hello"),
            AIMessage(content="Hi!"),
            SystemMessage(content="Note"),
        ]

        with patch("builtins.open", mock_open(read_data=yaml_content)):
            result = get_summary_prompt(messages)

        self.assertIn("Cliente: Hello", result)
        self.assertIn("Assistente: Hi!", result)
        self.assertIn("Sistema: Note", result)

    def test_uses_default_template_when_missing(self):
        """Test that default template is used when summary_prompt is missing."""
        yaml_content = "system_prompt: |\n  You are helpful.\n"
        messages = [HumanMessage(content="Test")]

        with patch("builtins.open", mock_open(read_data=yaml_content)):
            result = get_summary_prompt(messages)

        self.assertIn("Summarize the following conversation", result)
        self.assertIn("Cliente: Test", result)

    def test_formats_system_message_not_last(self):
        """Test that SystemMessage is formatted when not the last message."""
        yaml_content = "summary_prompt: |\n  Summarize:\n  {conversation}\n"
        messages = [
            HumanMessage(content="First"),
            SystemMessage(content="Context"),
            AIMessage(content="Last"),
        ]

        with patch("builtins.open", mock_open(read_data=yaml_content)):
            result = get_summary_prompt(messages)

        self.assertIn("Cliente: First", result)
        self.assertIn("Sistema: Context", result)
        self.assertIn("Assistente: Last", result)
