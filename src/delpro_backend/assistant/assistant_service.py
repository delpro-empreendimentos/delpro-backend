"""Core assistant service that orchestrates LLM conversation with memory and tool calling."""

import asyncio

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

from delpro_backend.assistant.agent_tools import build_tools
from delpro_backend.assistant.prompt_loader import build_chat_prompt, build_chat_prompt_from_text
from delpro_backend.db.chat_history_service import PostgresChatMessageHistory
from delpro_backend.db.db_service import AsyncSessionFactory
from delpro_backend.models.v1.database_models import PromptRow
from delpro_backend.services.media_service import MediaService
from delpro_backend.services.rag_service import RAGService
from delpro_backend.utils.logger import get_logger

logger = get_logger(__name__)

_PROMPT_ID = "main"


class AssistantService:
    """Service that manages conversational interactions with the LLM.

    Uses ``bind_tools`` for tool calling and manages conversation history
    manually via ``PostgresChatMessageHistory``.
    """

    def __init__(
        self,
        rag_service: RAGService,
        llm: ChatGoogleGenerativeAI,
        media_service: MediaService,
    ):
        """Initialize AssistantService with dependencies.

        Args:
            rag_service: Service for RAG context retrieval.
            llm: Primary LLM model for generating responses.
            media_service: Service for media CRUD and catalog.
            fallback_llm: Optional fallback LLM used when the primary hits quota limits.
        """
        self._rag_service = rag_service
        self._media_service = media_service
        self._llm = llm
        tools = build_tools(self._rag_service, self._media_service)
        self._llm_with_tools = self._llm.bind_tools(tools)
        self._tools_by_name = {t.name: t for t in tools}

    def _get_session_history(self, session_id: str) -> PostgresChatMessageHistory:
        """Create a PostgresChatMessageHistory for the given session.

        Args:
            session_id: The conversation/session identifier.

        Returns:
            A PostgresChatMessageHistory instance for the given session.
        """
        return PostgresChatMessageHistory(
            session_id=session_id,
            async_session_factory=AsyncSessionFactory,
        )

    async def _load_prompt_template(self) -> ChatPromptTemplate:
        """Load the system prompt from the database, falling back to YAML.

        Queries the ``agent_prompt`` table for the row with id='main'.
        If no row exists, falls back to the YAML-based prompt.

        Returns:
            A ChatPromptTemplate with the current system prompt.
        """
        async with AsyncSessionFactory() as session:
            row = await session.get(PromptRow, _PROMPT_ID)

        if row is not None:
            return build_chat_prompt_from_text(row.content)

        logger.info("No prompt row in DB, falling back to prompt.yml")
        return build_chat_prompt()

    @staticmethod
    def _extract_text(response) -> str:
        """Extract plain text from an LLM response.

        Args:
            response: The LLM response object.

        Returns:
            The extracted text content as a string.
        """
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

    async def _execute_tools(self, ai_message: AIMessage) -> list[ToolMessage]:
        """Execute all tool calls from an AIMessage in parallel.

        Builds coroutines only for known tools and runs them concurrently
        with ``asyncio.gather``. Unknown tools are added directly to the
        result list as error messages without being scheduled.

        Args:
            ai_message: The AIMessage containing tool_calls.

        Returns:
            List of ToolMessages with results, preserving the original call order.
        """
        tool_messages: list[ToolMessage | None] = [None] * len(ai_message.tool_calls)
        coroutines = []
        index_map: list[int] = []

        for idx, tool_call in enumerate(ai_message.tool_calls):
            tool_name = tool_call["name"]
            tool_fn = self._tools_by_name.get(tool_name)

            if tool_fn is None:
                logger.warning("Tool '%s' not found, skipping.", tool_name)
                tool_messages[idx] = ToolMessage(
                    content=f"Function {tool_name} failed to run",
                    tool_call_id=tool_call["id"],
                )
            else:
                coroutines.append(tool_fn.ainvoke(tool_call["args"]))
                index_map.append(idx)

        results = await asyncio.gather(*coroutines, return_exceptions=True)

        for coroutine_idx, result in enumerate(results):
            original_idx = index_map[coroutine_idx]
            tool_call = ai_message.tool_calls[original_idx]

            if isinstance(result, Exception):
                logger.exception("Tool '%s' failed: %s", tool_call["name"], result)
                content = f"Function {tool_call['name']} failed to run"
            else:
                content = str(result)

            tool_messages[original_idx] = ToolMessage(content=content, tool_call_id=tool_call["id"])

        return [msg for msg in tool_messages if msg is not None]

    async def chat(self, sender_phone_number: str, user_message: str, user_name: str) -> str:
        """Send a user message, run tool loop if needed, return final text.

        Execution follows a 2-round pattern:
        - Round 1: invoke LLM with prompt + history. If no tool_calls, return directly.
        - Round 2 (only if tool_calls): execute all tools in parallel, then invoke
          LLM again with tool results for the final answer.

        Args:
            sender_phone_number: Identifies the conversation (e.g., phone number).
            user_message: The user's input text.
            user_name: Name of the broker/user (from WhatsApp payload).
            phone_number: The user's WhatsApp phone number.

        Returns:
            The assistant's text response.
        """
        # 1. Load conversation history
        history_store = self._get_session_history(sender_phone_number)
        history_messages = await history_store.aget_messages()

        # 2. Load prompt from DB (falls back to YAML if no DB row)
        prompt_template = await self._load_prompt_template()

        # 3. Build prompt messages (system + history + current input)
        prompt_value = await prompt_template.ainvoke(
            {
                "input": user_message,
                "user_name": user_name,
                "sender_phone_number": sender_phone_number,
                "history": history_messages,
            }
        )
        messages = prompt_value.to_messages()

        # 4. Round 1: invoke LLM with tools bound (fallback on quota exhaustion)
        response = await self._llm_with_tools.ainvoke(messages)

        # 5. If no tool calls, return the text directly
        if not response.tool_calls:
            final_text = self._extract_text(response)
            await history_store.aadd_messages(
                [HumanMessage(content=user_message), AIMessage(content=final_text)]
            )
            return final_text

        # 6. Tool calls present: execute all tools in parallel
        logger.info(
            "Round 1 returned %d tool call(s), executing in parallel...", len(response.tool_calls)
        )
        tool_messages = await self._execute_tools(response)

        # 7. Round 2: re-invoke LLM with tool results for final answer
        messages.append(response)  # AIMessage with tool_calls
        messages.extend(tool_messages)  # ToolMessages with results

        # Use the same LLM that succeeded in round 1 for round 2
        active_llm = self._llm_with_tools

        final_response = await active_llm.ainvoke(messages)

        final_text = self._extract_text(final_response)

        # 8. Save only clean messages to history
        await history_store.aadd_messages(
            [HumanMessage(content=user_message), AIMessage(content=final_text)]
        )

        return final_text
