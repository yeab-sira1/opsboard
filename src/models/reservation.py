"""Reservation model: stock reserved against a product at a warehouse."""

from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Enum as SAEnum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from src.models.product import Product
    from src.models.warehouse import Warehouse


class ReservationStatus(enum.Enum):
    """Lifecycle states for a reservation."""

    ACTIVE = "ACTIVE"
    RELEASED = "RELEASED"
    FULFILLED = "FULFILLED"


class Reservation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A hold placed on stock that reduces availability without consuming it.

    Only reservations in the :attr:`ReservationStatus.ACTIVE` state count
    against available stock. A ``reference`` groups related reservations and is
    intentionally not unique.
    """

    __tablename__ = "reservations"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_reservation_quantity_positive"),
    )

    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id"))
    warehouse_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("warehouses.id"))
    quantity: Mapped[int] = mapped_column()
    reference: Mapped[str] = mapped_column(String(128), index=True)
    status: Mapped[ReservationStatus] = mapped_column(
        SAEnum(ReservationStatus, name="reservation_status"),
        default=ReservationStatus.ACTIVE,
    )

    product: Mapped["Product"] = relationship()
    warehouse: Mapped["Warehouse"] = relationship()

    def __repr__(self) -> str:
        return (
            f"Reservation(id={self.id!r}, reference={self.reference!r}, "
            f"quantity={self.quantity!r}, status={self.status.name})"
        )
