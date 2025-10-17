"""Notification model: an in-app/outbound message record."""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import Enum as SAEnum, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class NotificationStatus(enum.Enum):
    """Lifecycle states for a notification."""

    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"


class Notification(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A message queued for delivery.

    Delivery is modelled by the ``status``/``sent_at`` fields; no transport is
    performed at this layer.
    """

    __tablename__ = "notifications"

    subject: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[NotificationStatus] = mapped_column(
        SAEnum(NotificationStatus, name="notification_status"),
        default=NotificationStatus.PENDING,
    )
    sent_at: Mapped[datetime | None] = mapped_column(default=None)

    def __repr__(self) -> str:
        return (
            f"Notification(id={self.id!r}, subject={self.subject!r}, "
            f"status={self.status.name})"
        )
