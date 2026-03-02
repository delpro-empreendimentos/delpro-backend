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
