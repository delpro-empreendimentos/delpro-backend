"""Tests for prompt loading and ChatPromptTemplate construction."""

import os
import unittest
from unittest.mock import mock_open, patch

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from delpro_backend.assistant.prompt_loader import build_chat_prompt, load_prompt_config
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

    def test_uses_system_prompt_from_yaml(self):
        """Test that the system prompt is taken from YAML."""
        yaml_content = "system_prompt: My custom prompt\n"
        with patch("builtins.open", mock_open(read_data=yaml_content)):
            prompt = build_chat_prompt()
        system_msg = prompt.messages[0]
        self.assertIn("My custom prompt", str(system_msg))
