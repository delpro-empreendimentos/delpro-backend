"""Module for loading prompt configuration from YAML files."""

from pathlib import Path

import yaml
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

_PROMPT_DIR = Path(__file__).parent


def load_prompt_config(filename: str = "prompt.yml") -> dict:
    """Load the raw YAML prompt configuration.

    Args:
        filename: Name of the YAML file inside the assistant package directory.

    Returns:
        A dictionary with the parsed YAML content.

    Raises:
        FileNotFoundError: If the prompt file does not exist.
    """
    path = _PROMPT_DIR / filename
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def build_chat_prompt(filename: str = "prompt.yml") -> ChatPromptTemplate:
    """Build a LangChain ChatPromptTemplate from the YAML config.

    The template consists of:
    1. A system message (from the YAML ``system_prompt`` field).
    2. A ``MessagesPlaceholder`` for conversation history.
    3. A human message placeholder for the current user input.

    Args:
        filename: Name of the YAML file.

    Returns:
        A configured ChatPromptTemplate.
    """
    config = load_prompt_config(filename)
    system_prompt = config.get("system_prompt", "You are a helpful assistant.")

    return ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{input}"),
        ]
    )
