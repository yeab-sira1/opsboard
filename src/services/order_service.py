"""Order service: committed actions that consume reservations."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import NamedTuple

from sqlalchemy.orm import Session

from src.models.domain_event import DomainEventType
from src.models.order import Order, OrderStatus
from src.models.order_item import OrderItem
from src.models.reservation import ReservationStatus
from src.repositories import OrderRepository
from src.services.event_service import EventService
from src.services.reservation_service import ReservationService


class OrderLine(NamedTuple):
    """An order line request: a reservation and the quantity to commit."""

    reservation_id: uuid.UUID
    quantity: int


class OrderError(Exception):
    """Base class for order-related errors."""


class OrderNotFoundError(OrderError):
    """Raised when a referenced order does not exist."""

    def __init__(self, order_id: uuid.UUID) -> None:
        super().__init__(f"Order not found: {order_id}")
        self.order_id = order_id


class DuplicateOrderReferenceError(OrderError):
    """Raised when an order reference is already in use."""

    def __init__(self, reference: str) -> None:
        super().__init__(f"Order reference already exists: {reference}")
        self.reference = reference


class EmptyOrderError(OrderError):
    """Raised when an order is created without any line items."""

    def __init__(self, reference: str) -> None:
        super().__init__(f"Order has no items: {reference}")
        self.reference = reference


class InactiveReservationError(OrderError):
    """Raised when an order references a non-active reservation."""

    def __init__(self, reservation_id: uuid.UUID) -> None:
        super().__init__(f"Reservation is not active: {reservation_id}")
        self.reservation_id = reservation_id


class OrderQuantityMismatchError(OrderError):
    """Raised when a line quantity does not match its reservation."""

    def __init__(
        self, reservation_id: uuid.UUID, expected: int, requested: int
    ) -> None:
        super().__init__(
            f"Quantity mismatch for reservation {reservation_id}: "
            f"expected={expected}, requested={requested}"
        )
        self.reservation_id = reservation_id
        self.expected = expected
        self.requested = requested


class InvalidOrderStateError(OrderError):
    """Raised when an operation is invalid for the order's current state."""

    def __init__(self, order_id: uuid.UUID, status: OrderStatus) -> None:
        super().__init__(
            f"Invalid order state for operation: order={order_id}, "
            f"status={status.name}"
        )
        self.order_id = order_id
        self.status = status


class OrderService:
    """Manages the order lifecycle and integrates with reservations.

    Orders commit existing active reservations. Completion fulfills those
    reservations and cancellation releases them; reservation state changes are
    delegated to :class:`ReservationService` so inventory logic is never
    duplicated here. Physical stock is not modified by orders.
    """

    def __init__(self, session: Session) -> None:
        self._session = session
        self._orders = OrderRepository(session)
        self._reservations = ReservationService(session)
        self._events = EventService(session)

    def create_order(
        self, reference: str, lines: Sequence[OrderLine]
    ) -> Order:
        """Create a ``PENDING`` order from active reservations.

        Each line must reference an active reservation whose quantity matches
        the requested quantity.
        """
        if self._orders.get_by_reference(reference) is not None:
            raise DuplicateOrderReferenceError(reference)
        if not lines:
            raise EmptyOrderError(reference)

        order = Order(reference=reference, status=OrderStatus.PENDING)
        for line in lines:
            reservation = self._reservations.require_reservation(
                line.reservation_id
            )
            if reservation.status is not ReservationStatus.ACTIVE:
                raise InactiveReservationError(reservation.id)
            if line.quantity != reservation.quantity:
                raise OrderQuantityMismatchError(
                    reservation.id, reservation.quantity, line.quantity
                )
            order.items.append(
                OrderItem(
                    reservation_id=reservation.id, quantity=line.quantity
                )
            )

        return self._orders.add(order)

    def confirm_order(self, order_id: uuid.UUID) -> Order:
        """Transition a ``PENDING`` order to ``CONFIRMED``."""
        order = self._require_order(order_id)
        self._require_status(order, OrderStatus.PENDING)
        order.status = OrderStatus.CONFIRMED
        self._session.flush()
        return order

    def complete_order(self, order_id: uuid.UUID) -> Order:
        """Transition a ``CONFIRMED`` order to ``COMPLETED``.

        Fulfills every backing reservation. Physical stock is left unchanged.
        """
        order = self._require_order(order_id)
        self._require_status(order, OrderStatus.CONFIRMED)
        for item in order.items:
            self._reservations.fulfill_reservation(item.reservation_id)
        order.status = OrderStatus.COMPLETED
        self._session.flush()
        self._events.record_event(
            DomainEventType.ORDER_COMPLETED,
            {"order_id": str(order.id), "reference": order.reference},
        )
        return order

    def cancel_order(self, order_id: uuid.UUID) -> Order:
        """Cancel a ``PENDING`` or ``CONFIRMED`` order.

        Releases every backing reservation, restoring availability.
        """
        order = self._require_order(order_id)
        self._require_status(
            order, OrderStatus.PENDING, OrderStatus.CONFIRMED
        )
        for item in order.items:
            self._reservations.release_reservation(item.reservation_id)
        order.status = OrderStatus.CANCELLED
        self._session.flush()
        self._events.record_event(
            DomainEventType.ORDER_CANCELLED,
            {"order_id": str(order.id), "reference": order.reference},
        )
        return order

    def get_order(self, order_id: uuid.UUID) -> Order:
        """Return the order or raise :class:`OrderNotFoundError`."""
        return self._require_order(order_id)

    def get_orders_by_status(self, status: OrderStatus) -> list[Order]:
        """Return all orders in the given ``status``."""
        return self._orders.get_by_status(status)

    def get_all_orders(self) -> list[Order]:
        """Return all orders."""
        return self._orders.list()

    def _require_order(self, order_id: uuid.UUID) -> Order:
        order = self._orders.get(order_id)
        if order is None:
            raise OrderNotFoundError(order_id)
        return order

    @staticmethod
    def _require_status(order: Order, *allowed: OrderStatus) -> None:
        if order.status not in allowed:
            raise InvalidOrderStateError(order.id, order.status)
