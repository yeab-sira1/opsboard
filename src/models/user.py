"""User model."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from src.models.organization import Organization
    from src.models.role import Role


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A member of an organization."""

    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(50), unique=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)

    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("organizations.id"), default=None
    )
    role_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("roles.id"), default=None
    )

    organization: Mapped["Organization | None"] = relationship(
        back_populates="users"
    )
    role: Mapped["Role | None"] = relationship(back_populates="users")

    def __repr__(self) -> str:
        return f"User(id={self.id!r}, username={self.username!r})"
