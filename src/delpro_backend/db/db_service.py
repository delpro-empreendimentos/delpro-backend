"""Database Service class."""

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from delpro_backend.db.models import ResourceDocument, ResourceRow
from delpro_backend.utils.settings import settings

engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
)

AsyncSessionFactory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class DbService:
    """Database service providing CRUD operations for resources."""

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
