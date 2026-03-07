"""Database Service class."""

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from delpro_backend.models.v1.database_models import MessageRow, ResourceDocument, ResourceRow
from delpro_backend.utils.logger import get_logger
from delpro_backend.utils.settings import settings

logger_extra = {"component.name": "DbService", "component.version": "v1"}
logger = get_logger(__name__)

engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600,
    connect_args={"ssl": False},
)

AsyncSessionFactory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


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

        Optimized to use 2 queries instead of 3:
        1. Subquery to get IDs of oldest messages to delete
        2. DELETE with RETURNING to delete and fetch in one operation

        Args:
            session_id: The conversation/session identifier.
            max_messages: Maximum number of messages to keep.

        Returns:
            List of old messages that were deleted (empty if none).
        """
        async with AsyncSessionFactory() as session:
            # Subquery: get IDs of oldest messages that exceed the limit
            # This calculates (total - max_messages) in a single query
            ids_subquery = (
                select(MessageRow.id)
                .where(MessageRow.session_id == session_id)
                .order_by(MessageRow.created_at.asc())
                .limit(
                    select(func.greatest(0, func.count() - max_messages))
                    .where(MessageRow.session_id == session_id)
                    .correlate_except(MessageRow)
                    .scalar_subquery()
                )
            )

            # DELETE with RETURNING: delete and return data in one query
            delete_stmt = (
                delete(MessageRow)
                .where(MessageRow.id.in_(ids_subquery))
                .returning(MessageRow.role, MessageRow.content)
            )
            result = await session.execute(delete_stmt)
            deleted_rows = result.fetchall()
            await session.commit()

            if not deleted_rows:
                return []

            # Convert to BaseMessage
            old_messages: list[BaseMessage] = []
            for role, content in deleted_rows:
                if role == "human":
                    old_messages.append(HumanMessage(content=content))
                elif role == "ai":
                    old_messages.append(AIMessage(content=content))
                elif role == "system":
                    old_messages.append(SystemMessage(content=content))
                else:
                    old_messages.append(HumanMessage(content=content))

            logger.info("Deleted %d old messages for session %s", len(old_messages), session_id)

        return old_messages

    @staticmethod
    async def get_latest_summary(session_id: str) -> str | None:
        """Fetch the most recent summary (SystemMessage) content for a session.

        Args:
            session_id: The conversation/session identifier.

        Returns:
            The summary text, or None if no summary exists.
        """
        async with AsyncSessionFactory() as session:
            stmt = (
                select(MessageRow.content)
                .where(MessageRow.session_id == session_id, MessageRow.role == "system")
                .order_by(MessageRow.created_at.desc())
                .limit(1)
            )
            return await session.scalar(stmt)

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
