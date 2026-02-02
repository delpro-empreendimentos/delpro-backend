"""Database Service class."""

import logging

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from delpro_backend.db.models import MessageRow, ResourceDocument, ResourceRow
from delpro_backend.utils.settings import settings

logger = logging.getLogger(__name__)

engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
)

AsyncSessionFactory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


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


class DbService:
    """Database service providing CRUD operations for resources and chat messages."""

    @staticmethod
    async def save(resource: ResourceDocument) -> ResourceDocument:
        """Persist a ResourceDocument by id (upsert semantics).

        Inputs:
        resource: The ResourceDocument to store. Its id must be set by the backend.

        Returns:
        None.
        """
        async with AsyncSessionFactory() as session:
            returned_resource = await session.get(ResourceRow, resource.id)

            payload = resource.model_dump()

            if returned_resource is None:
                returned_resource = ResourceRow(id=resource.id, payload=payload)
                session.add(returned_resource)
            else:
                returned_resource.payload = payload

            await session.commit()

        return ResourceDocument.model_validate(returned_resource.payload)

    @staticmethod
    async def get(resource_id: str) -> ResourceDocument | None:
        """Retrieve a ResourceDocument by id.

        Inputs:
        resource_id: The resource id (UUID string).

        Returns:
        A ResourceDocument if found, otherwise None.
        """
        async with AsyncSessionFactory() as session:
            returned_resource = await session.get(ResourceRow, resource_id)

        return (
            ResourceDocument.model_validate(returned_resource.payload)
            if returned_resource
            else None
        )

    @staticmethod
    async def fetch_and_delete_old_messages(
        session_id: str,
        max_messages: int,
    ) -> list[BaseMessage]:
        """Fetch and delete old messages that exceed the limit.

        Args:
            session_id: The conversation/session identifier.
            max_messages: Maximum number of messages to keep.

        Returns:
            List of old messages that were deleted (empty if none).
        """
        async with AsyncSessionFactory() as session:
            # Count total messages
            count_stmt = select(func.count()).where(MessageRow.session_id == session_id)
            count_result = await session.execute(count_stmt)
            total_count = count_result.scalar_one()

            # If no need to delete, return empty
            if total_count <= max_messages:
                return []

            # Calculate how many messages to delete
            messages_to_delete = total_count - max_messages

            # Fetch old messages
            old_msgs_stmt = (
                select(MessageRow)
                .where(MessageRow.session_id == session_id)
                .order_by(MessageRow.created_at.asc())
                .limit(messages_to_delete)
            )
            old_result = await session.execute(old_msgs_stmt)
            old_rows = old_result.scalars().all()

            if not old_rows:
                logger.warning("No old messages found for session %s", session_id)
                return []

            # Convert to BaseMessage before deleting
            old_messages = [_row_to_message(row) for row in old_rows]

            # Delete old messages
            delete_stmt = delete(MessageRow).where(MessageRow.id.in_([row.id for row in old_rows]))
            await session.execute(delete_stmt)
            await session.commit()

            logger.info("Deleted %d old messages for session %s", len(old_rows), session_id)

        return old_messages

    @staticmethod
    async def insert_summary_message(session_id: str, summary_text: str) -> None:
        """Insert a SystemMessage with the summary.

        Args:
            session_id: The conversation/session identifier.
            summary_text: The summary text to insert.
        """
        # Truncate if too long
        MAX_SUMMARY_LENGTH = 4000
        if len(summary_text) > MAX_SUMMARY_LENGTH:
            summary_text = summary_text[:MAX_SUMMARY_LENGTH] + "..."
            logger.warning("Summary truncated for session %s", session_id)

        async with AsyncSessionFactory() as session:
            # Insert SystemMessage with summary
            summary_row = MessageRow(
                session_id=session_id,
                role="system",
                content=summary_text,
            )
            session.add(summary_row)
            await session.commit()

            logger.info("Inserted summary message for session %s", session_id)
