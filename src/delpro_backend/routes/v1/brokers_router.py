"""Router for broker CRUD operations."""

from fastapi import APIRouter, Query, Response, status
from fastapi.responses import JSONResponse

from delpro_backend.models.v1.broker_models import (
    BrokerListItem,
    BrokerResponse,
    CreateBrokerRequest,
    UpdateBrokerRequest,
)
from delpro_backend.services.broker_service import BrokerService
from delpro_backend.utils.handle_errors import handle_errors
from delpro_backend.utils.logger import get_logger

logger_extra = {"component.name": "BrokersRouter", "component.version": "v1"}
logger = get_logger(__name__)

brokers_router = APIRouter(prefix="/brokers", tags=["brokers"])

broker_service = BrokerService()


def _row_to_response(row) -> dict:
    """Convert a BrokerRow to a BrokerResponse dict."""
    return BrokerResponse(
        phone_number=row.phone_number,
        name=row.name,
        product_type_luxo=row.product_type_luxo,
        product_type_alto=row.product_type_alto,
        product_type_medio=row.product_type_medio,
        product_type_mcmv=row.product_type_mcmv,
        sell_type_investimento=row.sell_type_investimento,
        sell_type_moradia=row.sell_type_moradia,
        region_zona_norte=row.region_zona_norte,
        region_zona_sul=row.region_zona_sul,
        region_zona_central=row.region_zona_central,
        interactions=row.interactions,
        date_joined=row.date_joined,
        last_message_at=row.last_message_at,
        sold_delpro_product=row.sold_delpro_product,
    ).model_dump(mode="json")


@brokers_router.get("")
@handle_errors
async def list_brokers(
    sort_by: str = Query(default="interactions"),
    order: str = Query(default="desc"),
    search: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=200),
):
    """List brokers with sorting, optional name search, and pagination."""
    rows, total = await broker_service.list_brokers(
        sort_by=sort_by, order=order, search=search, skip=skip, limit=limit
    )

    items = [
        BrokerListItem(
            phone_number=r.phone_number,
            name=r.name,
            interactions=r.interactions,
            date_joined=r.date_joined,
            last_message_at=r.last_message_at,
            sold_delpro_product=r.sold_delpro_product,
        ).model_dump(mode="json")
        for r in rows
    ]

    return JSONResponse(status_code=status.HTTP_200_OK, content={"items": items, "total": total})


@brokers_router.get("/{phone_number}")
@handle_errors
async def get_broker(phone_number: str):
    """Get a single broker by phone number."""
    row = await broker_service.get_broker(phone_number)
    return JSONResponse(status_code=status.HTTP_200_OK, content=_row_to_response(row))


@brokers_router.post("")
@handle_errors
async def create_broker(data: CreateBrokerRequest):
    """Create a broker manually."""
    row = await broker_service.create_broker(data)
    return JSONResponse(status_code=status.HTTP_201_CREATED, content=_row_to_response(row))


@brokers_router.put("/{phone_number}")
@handle_errors
async def update_broker(phone_number: str, data: UpdateBrokerRequest):
    """Update broker fields."""
    row = await broker_service.update_broker(phone_number, data)
    return JSONResponse(status_code=status.HTTP_200_OK, content=_row_to_response(row))


@brokers_router.delete("/{phone_number}")
@handle_errors
async def delete_broker(phone_number: str):
    """Delete a broker."""
    await broker_service.delete_broker(phone_number)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
