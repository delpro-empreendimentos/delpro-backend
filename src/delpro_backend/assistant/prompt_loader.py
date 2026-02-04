"""Module for loading prompt configuration from YAML files."""

from collections.abc import Sequence
from pathlib import Path

import yaml
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
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


def get_summary_prompt(messages: Sequence[BaseMessage], filename: str = "prompt.yml") -> str:
    """Build a summary prompt from conversation messages.

    Args:
        messages: Sequence of messages to summarize.
        filename: Name of the YAML file containing the summary prompt template.

    Returns:
        The formatted summary prompt ready to send to the LLM.
    """
    config = load_prompt_config(filename)
    summary_template = config.get(
        "summary_prompt",
        "Summarize the following conversation:\n{conversation}",
    )

    # Format messages as conversation text
    conversation = []
    for msg in messages:
        if isinstance(msg, HumanMessage):
            conversation.append(f"Cliente: {msg.content}")
        elif isinstance(msg, AIMessage):
            # Handle both string and dict content
            content = msg.content
            if isinstance(content, list) and len(content) > 0:
                first_item = content[0]
                if isinstance(first_item, dict):
                    content = first_item.get("text", str(content))
                else:
                    content = str(first_item)
            elif not isinstance(content, str):
                content = str(content)
            conversation.append(f"Assistente: {content}")
        elif isinstance(msg, SystemMessage):
            conversation.append(f"Sistema: {msg.content}")

    conversation_text = "\n".join(conversation)

    # Substitute conversation into template
    return summary_template.format(conversation=conversation_text)
