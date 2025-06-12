"""Product model."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from src.models.stock_record import StockRecord


class Product(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A stockable item identified by a unique SKU."""

    __tablename__ = "products"

    sku: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(String(1000), default=None)
    unit: Mapped[str] = mapped_column(String(16))

    stock_records: Mapped[list["StockRecord"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"Product(id={self.id!r}, sku={self.sku!r})"
