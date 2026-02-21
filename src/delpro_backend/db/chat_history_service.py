"""Async PostgreSQL-backed chat message history for LangChain."""

from __future__ import annotations

from collections.abc import Sequence

from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

# from delpro_backend.db.db_service import DbService
from delpro_backend.models.v1.database_models import MessageRow
from delpro_backend.utils.logger import get_logger
from delpro_backend.utils.settings import settings

logger_extra = {"component.name": "ChatHistoryService", "component.version": "v1"}
logger = get_logger(__name__)

# db_service = DbService()


def _row_to_message(row: MessageRow) -> BaseMessage:
    """Convert a MessageRow to the corresponding LangChain message type.

    Args:
        row: The database row to convert.

    Returns:
        A LangChain message object.
    """
    if row.role == "human":
        return HumanMessage(content=row.content)
    if row.role == "ai":
        return AIMessage(content=row.content)
    if row.role == "system":
        return SystemMessage(content=row.content)
    return HumanMessage(content=row.content)


def _message_to_role(message: BaseMessage) -> str:
    """Extract the role string from a LangChain message."""
    if isinstance(message, HumanMessage):
        return "human"
    if isinstance(message, AIMessage):
        return "ai"
    if isinstance(message, SystemMessage):
        return "system"
    return "human"


class PostgresChatMessageHistory(BaseChatMessageHistory):
    """Chat message history backed by PostgreSQL via async SQLAlchemy.

    The async methods (``aget_messages``, ``aadd_messages``, ``aclear``) are the
    primary interface.  The sync variants raise ``NotImplementedError`` because
    the application is fully async.
    """

    def __init__(
        self,
        session_id: str,
        async_session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        """Initialize with a session ID and async session factory.

        Args:
            session_id: The conversation/session identifier.
            async_session_factory: Factory for creating async database sessions.
        """
        self._session_id = session_id
        self._async_session_factory = async_session_factory

    @property
    def messages(self) -> list[BaseMessage]:
        """Sync access not supported -- use aget_messages."""
        raise NotImplementedError("Use aget_messages() in async context.")

    # --- Summarization (disabled) ---
    # To enable: uncomment _asummarize_old_messages, add the fire-and-forget
    # call in aadd_messages, and restore imports (asyncio, DbService,
    # get_summary_llm, get_summary_prompt).
    #
    # async def _asummarize_old_messages(self) -> None:
    #     """Summarize and replace old messages with a SystemMessage.

    #     This method runs asynchronously in the background (fire-and-forget).
    #     It fetches old messages, generates a summary using LLM, and replaces
    #     them with a single SystemMessage.

    #     Error handling: All exceptions are caught and logged. Failures do not
    #     propagate to avoid disrupting the main flow.
    #     """
    #     try:
    #         # Fetch and delete old messages
    #         old_messages = await db_service.fetch_and_delete_old_messages(
    #             self._session_id, settings.MAX_HISTORY_MESSAGES
    #         )

    #         if not old_messages:
    #             return  # Nothing to summarize

    #         # Generate summary with LLM (using summary-specific config)
    #         llm = get_summary_llm()
    #         summary_prompt = get_summary_prompt(old_messages)
    #         response = await llm.ainvoke(summary_prompt)

    #         # Extract text from response
    #         if hasattr(response, "content"):
    #             content = response.content
    #             if isinstance(content, list) and len(content) > 0:
    #                 first_item = content[0]
    #                 if isinstance(first_item, dict):
    #                     summary_text = first_item.get("text", str(content))
    #                 else:
    #                     summary_text = str(first_item)
    #             elif isinstance(content, str):
    #                 summary_text = content
    #             else:
    #                 summary_text = str(content)
    #         else:
    #             summary_text = str(response)

    #         # Insert summary message
    #         await db_service.insert_summary_message(self._session_id, summary_text)

    #         logger.info("Successfully summarized messages for session %s", self._session_id)

    #     except Exception as e:
    #         logger.exception(
    #             "Failed to generate summary for session %s: %s",
    #             self._session_id,
    #             str(e),
    #         )
    #         # Do not propagate - this is a background task

    async def aget_messages(self) -> list[BaseMessage]:
        """Load the last N messages for this session, ordered by creation time."""
        async with self._async_session_factory() as session:
            stmt = (
                select(MessageRow)
                .where(MessageRow.session_id == self._session_id)
                .order_by(MessageRow.created_at.desc())
                .limit(settings.MAX_HISTORY_MESSAGES)
            )
            result = await session.execute(stmt)
            rows = result.scalars().all()
        return [_row_to_message(row) for row in reversed(rows)]

    async def aadd_messages(self, messages: Sequence[BaseMessage]) -> None:
        """Persist one or more messages for this session."""
        async with self._async_session_factory() as session:
            for msg in messages:
                row = MessageRow(
                    session_id=self._session_id,
                    role=_message_to_role(msg),
                    content=msg.content if isinstance(msg.content, str) else str(msg.content),
                )
                session.add(row)
            await session.commit()

        # To enable summarization, uncomment:
        # asyncio.create_task(self._asummarize_old_messages())

    def clear(self) -> None:
        """Sync clear not supported -- use aclear."""
        raise NotImplementedError("Use aclear() in async context.")

    async def aclear(self) -> None:
        """Delete all messages for this session."""
        async with self._async_session_factory() as session:
            stmt = select(MessageRow).where(MessageRow.session_id == self._session_id)
            result = await session.execute(stmt)
            for row in result.scalars().all():
                await session.delete(row)
            await session.commit()
