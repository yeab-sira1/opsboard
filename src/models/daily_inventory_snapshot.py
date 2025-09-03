"""Daily inventory snapshot model: a point-in-time stock aggregate."""

from __future__ import annotations

import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from src.models.product import Product
    from src.models.warehouse import Warehouse


class DailyInventorySnapshot(UUIDPrimaryKeyMixin, Base):
    """A recorded stock position for a product/warehouse on a given date.

    Captures the physical, reserved, and available quantities so historical
    inventory can be reported without recomputing past availability. Exactly
    one snapshot exists per (date, product, warehouse).
    """

    __tablename__ = "daily_inventory_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "snapshot_date",
            "product_id",
            "warehouse_id",
            name="uq_snapshot_date_product_warehouse",
        ),
    )

    snapshot_date: Mapped[date] = mapped_column(Date, index=True)
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id"))
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("warehouses.id")
    )
    physical_stock: Mapped[int] = mapped_column()
    reserved_quantity: Mapped[int] = mapped_column()
    available_stock: Mapped[int] = mapped_column()

    product: Mapped["Product"] = relationship()
    warehouse: Mapped["Warehouse"] = relationship()

    def __repr__(self) -> str:
        return (
            f"DailyInventorySnapshot(date={self.snapshot_date!r}, "
            f"product_id={self.product_id!r}, "
            f"warehouse_id={self.warehouse_id!r}, "
            f"available={self.available_stock!r})"
        )
