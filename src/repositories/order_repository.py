"""Repository for :class:`Order` persistence."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.order import Order, OrderStatus
from src.repositories.base_repository import BaseRepository


class OrderRepository(BaseRepository[Order]):
    """CRUD operations and lookups for orders."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, Order)

    def get_by_reference(self, reference: str) -> Order | None:
        """Return the order with ``reference`` or ``None`` if absent."""
        return self._session.scalar(
            select(Order).where(Order.reference == reference)
        )

    def get_by_status(self, status: OrderStatus) -> list[Order]:
        """Return all orders in the given ``status``."""
        return list(
            self._session.scalars(
                select(Order).where(Order.status == status)
            ).all()
        )
