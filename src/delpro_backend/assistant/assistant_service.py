"""Core assistant service that orchestrates LLM conversation with memory."""

from langchain_core.messages import SystemMessage
from langchain_core.runnables.history import RunnableWithMessageHistory

from delpro_backend.assistant.prompt_loader import build_chat_prompt
from delpro_backend.db.chat_history_service import PostgresChatMessageHistory
from delpro_backend.db.db_service import AsyncSessionFactory
from delpro_backend.utils.llm_builder import get_llm


class AssistantService:
    """Service that manages conversational interactions with the LLM.

    Wires together the prompt template, chat model, and persistent
    message history into a single ``RunnableWithMessageHistory`` chain.
    """

    _chain_with_history: RunnableWithMessageHistory | None = None

    @classmethod
    def _get_chain(cls) -> RunnableWithMessageHistory:
        """Build (or return cached) the conversation chain.

        Returns:
            The runnable chain with message history.
        """
        if cls._chain_with_history is None:
            prompt = build_chat_prompt()
            llm = get_llm()
            chain = prompt | llm

            cls._chain_with_history = RunnableWithMessageHistory(
                chain,
                get_session_history=cls._get_session_history,
                input_messages_key="input",
                history_messages_key="history",
            )

        return cls._chain_with_history

    @staticmethod
    def _get_session_history(session_id: str) -> PostgresChatMessageHistory:
        """Factory function for RunnableWithMessageHistory.

        Args:
            session_id: The conversation/session identifier.

        Returns:
            A PostgresChatMessageHistory instance for the given session.
        """
        return PostgresChatMessageHistory(
            session_id=session_id,
            async_session_factory=AsyncSessionFactory,
        )

    @staticmethod
    async def chat(session_id: str, user_message: str, user_name: str) -> str:
        """Send a user message and get the assistant's response.

        Args:
            session_id: Identifies the conversation (e.g., phone number).
            user_message: The user's input text.
            user_name: Name of the broker/user (from WhatsApp payload).

        Returns:
            The assistant's text response.
        """
        chain = __class__._get_chain()

        # Build dynamic context info
        context_parts = [f"Corretor: {user_name}"]

        # Get conversation history to check for context summary
        history = await PostgresChatMessageHistory(
            session_id=session_id,
            async_session_factory=AsyncSessionFactory,
        ).aget_messages()

        # Look for most recent SystemMessage (summary)
        summary_text = None
        for msg in reversed(history):
            if isinstance(msg, SystemMessage):
                summary_text = msg.content
                break

        if summary_text:
            context_parts.append(f"Contexto anterior: {summary_text[:500]}")  # Limit to 500 chars

        context_info = "\n".join(context_parts)

        # Invoke chain with dynamic variables
        response = await chain.ainvoke(
            {
                "input": user_message,
                "context_info": context_info,
            },
            config={"configurable": {"session_id": session_id}},
        )

        # Extract text from response
        if hasattr(response, "content"):
            content = response.content
            if isinstance(content, list) and len(content) > 0:
                first_item = content[0]
                if isinstance(first_item, dict):
                    return first_item.get("text", str(content))
                else:
                    return str(first_item)
            elif isinstance(content, str):
                return content
            else:
                return str(content)
        else:
            return str(response)
