"""Warehouse model."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from src.models.stock_record import StockRecord


class Warehouse(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A physical location that holds product stock."""

    __tablename__ = "warehouses"

    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    location: Mapped[str] = mapped_column(String(255))

    stock_records: Mapped[list["StockRecord"]] = relationship(
        back_populates="warehouse",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"Warehouse(id={self.id!r}, code={self.code!r})"
