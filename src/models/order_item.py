"""Order item model: a single line of an order tied to a reservation."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from src.models.order import Order
    from src.models.reservation import Reservation


class OrderItem(UUIDPrimaryKeyMixin, Base):
    """One line of an order, backed by a single reservation."""

    __tablename__ = "order_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_order_item_quantity_positive"),
    )

    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id"))
    reservation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("reservations.id")
    )
    quantity: Mapped[int] = mapped_column()

    order: Mapped["Order"] = relationship(back_populates="items")
    reservation: Mapped["Reservation"] = relationship()

    def __repr__(self) -> str:
        return (
            f"OrderItem(id={self.id!r}, order_id={self.order_id!r}, "
            f"reservation_id={self.reservation_id!r}, quantity={self.quantity!r})"
        )
