"""Service for broker CRUD operations."""

import datetime

from sqlalchemy import func, select

from delpro_backend.db.db_service import AsyncSessionFactory
from delpro_backend.models.v1.broker_models import CreateBrokerRequest, UpdateBrokerRequest
from delpro_backend.models.v1.database_models import BrokerRow, MessageRow
from delpro_backend.models.v1.exception_models import InvalidRequestError, ResourceNotFoundError
from delpro_backend.utils.logger import get_logger

logger_extra = {"component.name": "BrokerService", "component.version": "v1"}
logger = get_logger(__name__)


class BrokerService:
    """Service for broker CRUD operations."""

    async def create_broker(self, data: CreateBrokerRequest) -> BrokerRow:
        """Create a new broker profile."""
        async with AsyncSessionFactory() as session:
            existing = await session.get(BrokerRow, data.phone_number)
            if existing:
                raise InvalidRequestError(f"Broker with phone '{data.phone_number}' already exists")

            row = BrokerRow(
                phone_number=data.phone_number,
                name=data.name,
                product_type_luxo=data.product_type_luxo,
                product_type_alto=data.product_type_alto,
                product_type_medio=data.product_type_medio,
                product_type_mcmv=data.product_type_mcmv,
                sell_type_investimento=data.sell_type_investimento,
                sell_type_moradia=data.sell_type_moradia,
                region_zona_norte=data.region_zona_norte,
                region_zona_sul=data.region_zona_sul,
                region_zona_central=data.region_zona_central,
                interactions=0,
                sold_delpro_product=data.sold_delpro_product,
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return row

    async def get_broker(self, phone_number: str) -> BrokerRow:
        """Retrieve a broker by phone number (O(1) primary key lookup)."""
        async with AsyncSessionFactory() as session:
            row = await session.get(BrokerRow, phone_number)
            if not row:
                raise ResourceNotFoundError("Broker", phone_number)
            return row

    async def list_brokers(
        self,
        sort_by: str = "interactions",
        order: str = "desc",
        search: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[BrokerRow], int]:
        """List brokers with sorting, optional name search, and pagination."""
        allowed_sort = {"interactions", "date_joined", "name", "last_message_at"}
        if sort_by not in allowed_sort:
            sort_by = "interactions"

        async with AsyncSessionFactory() as session:
            base = select(BrokerRow)
            if search:
                base = base.where(BrokerRow.name.ilike(f"%{search}%"))

            count_stmt = select(func.count()).select_from(base.subquery())
            total: int = (await session.execute(count_stmt)).scalar_one()

            col = getattr(BrokerRow, sort_by)
            ordered = col.desc() if order == "desc" else col.asc()
            stmt = base.order_by(ordered).offset(skip).limit(limit)
            result = await session.execute(stmt)
            return list(result.scalars().all()), total

    async def update_broker(self, phone_number: str, data: UpdateBrokerRequest) -> BrokerRow:
        """Update broker fields (partial update)."""
        async with AsyncSessionFactory() as session:
            row = await session.get(BrokerRow, phone_number)
            if not row:
                raise ResourceNotFoundError("Broker", phone_number)

            update_data = data.model_dump(exclude_none=True)
            for field, value in update_data.items():
                setattr(row, field, value)

            await session.commit()
            await session.refresh(row)
            return row

    async def delete_broker(self, phone_number: str) -> None:
        """Delete a broker by phone number."""
        async with AsyncSessionFactory() as session:
            row = await session.get(BrokerRow, phone_number)
            if not row:
                raise ResourceNotFoundError("Broker", phone_number)

            await session.delete(row)
            await session.commit()

        logger.info("Deleted broker %s", phone_number, extra=logger_extra)

    async def get_messages(
        self,
        phone_number: str,
        skip: int = 0,
        limit: int = 30,
    ) -> tuple[list[MessageRow], int]:
        """Return paginated chat messages for a broker (newest first)."""
        async with AsyncSessionFactory() as session:
            base = select(MessageRow).where(MessageRow.session_id == phone_number)

            count_stmt = select(func.count()).select_from(base.subquery())
            total: int = (await session.execute(count_stmt)).scalar_one()

            stmt = base.order_by(MessageRow.created_at.desc()).offset(skip).limit(limit)
            result = await session.execute(stmt)
            return list(result.scalars().all()), total

    async def upsert_from_interaction(self, phone_number: str, name: str) -> BrokerRow:
        """Create or update broker from a WhatsApp interaction.

        If broker doesn't exist: create with interactions=1, date_joined=now.
        If broker exists: increment interactions, update last_message_at and name.
        """
        now = datetime.datetime.now(datetime.UTC)

        async with AsyncSessionFactory() as session:
            row = await session.get(BrokerRow, phone_number)

            if row is None:
                row = BrokerRow(
                    phone_number=phone_number,
                    name=name,
                    interactions=1,
                    date_joined=now,
                    last_message_at=now,
                )
                session.add(row)
            else:
                row.interactions += 1
                row.last_message_at = now
                if name:
                    row.name = name

            await session.commit()
            await session.refresh(row)
            return row
