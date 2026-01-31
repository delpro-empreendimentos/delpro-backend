"""File that defines API and database models for resources."""

from pydantic import BaseModel
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for SQLAlchemy ORM models."""

    pass


class ResourceRow(Base):
    """ORM model that maps the resources table."""

    __tablename__ = "resources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)


class ResourceDocument(BaseModel):
    """Pydantic model representing a resource document."""

    id: str
    text: str
