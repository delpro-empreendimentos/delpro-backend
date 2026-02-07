"""Core assistant service that orchestrates LLM conversation with memory."""

from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_google_genai import ChatGoogleGenerativeAI

from delpro_backend.assistant.prompt_loader import build_chat_prompt
from delpro_backend.db.chat_history_service import PostgresChatMessageHistory
from delpro_backend.db.db_service import AsyncSessionFactory
from delpro_backend.services.rag_service import RAGService


class AssistantService:
    """Service that manages conversational interactions with the LLM.

    Wires together the prompt template, chat model, and persistent
    message history into a single ``RunnableWithMessageHistory`` chain.
    """

    def __init__(self, rag_service: RAGService, llm: ChatGoogleGenerativeAI):
        """Initialize AssistantService with dependencies.

        Args:
            rag_service: Service for RAG context retrieval
            llm: LLM model for generating responses
        """
        self._rag_service = rag_service
        self._llm = llm
        self._chain_with_history: RunnableWithMessageHistory | None = None

    def _get_chain(self) -> RunnableWithMessageHistory:
        """Build (or return cached) the conversation chain.

        Returns:
            The runnable chain with message history.
        """
        if self._chain_with_history is None:
            prompt = build_chat_prompt()
            chain = prompt | self._llm

            self._chain_with_history = RunnableWithMessageHistory(
                chain,
                get_session_history=self._get_session_history,
                input_messages_key="input",
                history_messages_key="history",
            )

        return self._chain_with_history

    def _get_session_history(self, session_id: str) -> PostgresChatMessageHistory:
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

    async def chat(self, session_id: str, user_message: str, user_name: str) -> str:
        """Send a user message and get the assistant's response.

        Args:
            session_id: Identifies the conversation (e.g., phone number).
            user_message: The user's input text.
            user_name: Name of the broker/user (from WhatsApp payload).

        Returns:
            The assistant's text response.
        """
        # Fetch summary and RAG context in parallel
        # summary_task = db_service.get_latest_summary(session_id)
        rag_result = await self._rag_service.retrieve_context(user_message)

        # summary_text, rag_result = await asyncio.gather(summary_task, rag_task)

        chain = self._get_chain()
        response = await chain.ainvoke(
            {
                "input": user_message,
                "user_name": user_name,
                "user_input": user_message,
                # "context_info": summary_text,
                "rag_context": rag_result,
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
                return str(first_item)
            elif isinstance(content, str):
                return content
            return str(content)
        return str(response)
