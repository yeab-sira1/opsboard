"""Notification category model."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from src.models.notification_preference import NotificationPreference
    from src.models.notification_template import NotificationTemplate


class NotificationCategory(UUIDPrimaryKeyMixin, Base):
    """A grouping of notifications that can be templated and toggled."""

    __tablename__ = "notification_categories"

    name: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str | None] = mapped_column(String(255), default=None)

    templates: Mapped[list["NotificationTemplate"]] = relationship(
        back_populates="category",
        cascade="all, delete-orphan",
    )
    preferences: Mapped[list["NotificationPreference"]] = relationship(
        back_populates="category",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"NotificationCategory(id={self.id!r}, name={self.name!r})"
        )
