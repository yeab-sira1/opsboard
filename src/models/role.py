"""Role model."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from src.models.user import User


class Role(UUIDPrimaryKeyMixin, Base):
    """A named role that can be assigned to users."""

    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(String(50), unique=True)
    description: Mapped[str | None] = mapped_column(String(255), default=None)

    users: Mapped[list["User"]] = relationship(back_populates="role")

    def __repr__(self) -> str:
        return f"Role(id={self.id!r}, name={self.name!r})"
