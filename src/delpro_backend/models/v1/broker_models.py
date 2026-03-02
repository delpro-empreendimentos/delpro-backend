"""Pydantic models for broker endpoints."""

from datetime import datetime

from pydantic import BaseModel, Field


class CreateBrokerRequest(BaseModel):
    """Request body for POST /brokers."""

    phone_number: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=1, max_length=255)
    product_type_luxo: bool = False
    product_type_alto: bool = False
    product_type_medio: bool = False
    product_type_mcmv: bool = False
    sell_type_investimento: bool = False
    sell_type_moradia: bool = False
    region_zona_norte: bool = False
    region_zona_sul: bool = False
    region_zona_central: bool = False
    sold_delpro_product: bool = False


class UpdateBrokerRequest(BaseModel):
    """Request body for PUT /brokers/{phone_number}."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    product_type_luxo: bool | None = None
    product_type_alto: bool | None = None
    product_type_medio: bool | None = None
    product_type_mcmv: bool | None = None
    sell_type_investimento: bool | None = None
    sell_type_moradia: bool | None = None
    region_zona_norte: bool | None = None
    region_zona_sul: bool | None = None
    region_zona_central: bool | None = None
    sold_delpro_product: bool | None = None


class BrokerResponse(BaseModel):
    """Full broker response with all fields."""

    phone_number: str
    name: str
    product_type_luxo: bool
    product_type_alto: bool
    product_type_medio: bool
    product_type_mcmv: bool
    sell_type_investimento: bool
    sell_type_moradia: bool
    region_zona_norte: bool
    region_zona_sul: bool
    region_zona_central: bool
    interactions: int
    date_joined: datetime
    last_message_at: datetime
    sold_delpro_product: bool


class BrokerListItem(BaseModel):
    """Single broker item in list response."""

    phone_number: str
    name: str
    interactions: int
    date_joined: datetime
    last_message_at: datetime
    sold_delpro_product: bool


class MessageResponse(BaseModel):
    """Single chat message in history response."""

    role: str
    content: str
    created_at: datetime
