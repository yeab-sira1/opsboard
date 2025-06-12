"""Stock record model: current inventory of a product at a warehouse."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from src.models.product import Product
    from src.models.warehouse import Warehouse


class StockRecord(UUIDPrimaryKeyMixin, Base):
    """The on-hand quantity of one product at one warehouse.

    Exactly one record exists per (product, warehouse) pair, and the quantity
    is constrained to be non-negative at the database level.
    """

    __tablename__ = "stock_records"
    __table_args__ = (
        UniqueConstraint(
            "product_id", "warehouse_id", name="uq_stock_product_warehouse"
        ),
        CheckConstraint("quantity >= 0", name="ck_stock_quantity_non_negative"),
    )

    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id"))
    warehouse_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("warehouses.id"))
    quantity: Mapped[int] = mapped_column(default=0)

    product: Mapped["Product"] = relationship(back_populates="stock_records")
    warehouse: Mapped["Warehouse"] = relationship(back_populates="stock_records")

    def __repr__(self) -> str:
        return (
            f"StockRecord(product_id={self.product_id!r}, "
            f"warehouse_id={self.warehouse_id!r}, quantity={self.quantity!r})"
        )
