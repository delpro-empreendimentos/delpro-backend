"""File that defines API and database models for resources."""

import datetime

from pydantic import BaseModel
from sqlalchemy import DateTime, String, Text, func
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


class MessageRow(Base):
    """ORM model that maps the conversation_messages table."""

    __tablename__ = "conversation_messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class ResourceDocument(BaseModel):
    """Pydantic model representing a resource document."""

    id: str
    text: str
