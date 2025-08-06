"""Order model: a committed business action over reserved stock."""

from __future__ import annotations

import enum
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from src.models.order_item import OrderItem


class OrderStatus(enum.Enum):
    """Lifecycle states for an order."""

    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"


class Order(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A customer/operations order composed of one or more line items."""

    __tablename__ = "orders"

    reference: Mapped[str] = mapped_column(String(128), unique=True)
    status: Mapped[OrderStatus] = mapped_column(
        SAEnum(OrderStatus, name="order_status"),
        default=OrderStatus.PENDING,
    )

    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"Order(id={self.id!r}, reference={self.reference!r}, "
            f"status={self.status.name})"
        )
