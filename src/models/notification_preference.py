"""Notification preference model."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from src.models.notification_category import NotificationCategory


class NotificationPreference(UUIDPrimaryKeyMixin, Base):
    """Whether notifications in a category are enabled.

    Exactly one preference exists per category; a missing preference is treated
    as enabled by the service layer.
    """

    __tablename__ = "notification_preferences"
    __table_args__ = (
        UniqueConstraint(
            "category_id", name="uq_notification_preference_category"
        ),
    )

    category_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("notification_categories.id")
    )
    enabled: Mapped[bool] = mapped_column(default=True)

    category: Mapped["NotificationCategory"] = relationship(
        back_populates="preferences"
    )

    def __repr__(self) -> str:
        return (
            f"NotificationPreference(id={self.id!r}, "
            f"category_id={self.category_id!r}, enabled={self.enabled!r})"
        )
