"""Domain event model: a recorded business event."""

from __future__ import annotations

import enum

from sqlalchemy import Enum as SAEnum, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class DomainEventType(enum.Enum):
    """Categories of business event that can be recorded."""

    ORDER_COMPLETED = "ORDER_COMPLETED"
    ORDER_CANCELLED = "ORDER_CANCELLED"
    REPORT_GENERATED = "REPORT_GENERATED"
    NOTIFICATION_SENT = "NOTIFICATION_SENT"
    STOCK_IMPORTED = "STOCK_IMPORTED"
    STOCK_IMPORT_FAILED = "STOCK_IMPORT_FAILED"


class DomainEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """An immutable record that a business event occurred.

    ``payload_json`` carries an opaque JSON string describing the event; it is
    not interpreted at the storage layer.
    """

    __tablename__ = "domain_events"

    event_type: Mapped[DomainEventType] = mapped_column(
        SAEnum(DomainEventType, name="domain_event_type")
    )
    payload_json: Mapped[str] = mapped_column(Text, default="{}")

    def __repr__(self) -> str:
        return (
            f"DomainEvent(id={self.id!r}, event_type={self.event_type.name})"
        )
