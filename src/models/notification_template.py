"""Notification template model."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from src.models.notification_category import NotificationCategory


class NotificationTemplate(UUIDPrimaryKeyMixin, Base):
    """A reusable subject/body template belonging to a category.

    The ``subject_template`` and ``body_template`` are ``str.format`` strings
    rendered against a context at send time.
    """

    __tablename__ = "notification_templates"

    name: Mapped[str] = mapped_column(String(100), unique=True)
    subject_template: Mapped[str] = mapped_column(String(255))
    body_template: Mapped[str] = mapped_column(Text)
    category_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("notification_categories.id")
    )

    category: Mapped["NotificationCategory"] = relationship(
        back_populates="templates"
    )

    def __repr__(self) -> str:
        return (
            f"NotificationTemplate(id={self.id!r}, name={self.name!r})"
        )
