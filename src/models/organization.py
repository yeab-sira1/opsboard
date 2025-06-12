"""Organization model."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from src.models.user import User


class Organization(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A tenant organization that owns users and operational data."""

    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(120), unique=True)

    users: Mapped[list["User"]] = relationship(
        back_populates="organization",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"Organization(id={self.id!r}, name={self.name!r})"
