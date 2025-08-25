"""Reservation service: availability-aware holds on inventory stock."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from src.models.reservation import Reservation, ReservationStatus
from src.repositories import ReservationRepository
from src.services.inventory_service import InventoryService


class ReservationError(Exception):
    """Base class for reservation-related errors."""


class ReservationNotFoundError(ReservationError):
    """Raised when a referenced reservation does not exist."""

    def __init__(self, reservation_id: uuid.UUID) -> None:
        super().__init__(f"Reservation not found: {reservation_id}")
        self.reservation_id = reservation_id


class ReservationAlreadyReleasedError(ReservationError):
    """Raised when releasing a reservation that is already released."""

    def __init__(self, reservation_id: uuid.UUID) -> None:
        super().__init__(f"Reservation already released: {reservation_id}")
        self.reservation_id = reservation_id


class ReservationAlreadyFulfilledError(ReservationError):
    """Raised when a reservation has already been fulfilled."""

    def __init__(self, reservation_id: uuid.UUID) -> None:
        super().__init__(f"Reservation already fulfilled: {reservation_id}")
        self.reservation_id = reservation_id


class InvalidReservationQuantityError(ReservationError):
    """Raised when a reservation quantity is not strictly positive."""

    def __init__(self, quantity: int) -> None:
        super().__init__(f"Reservation quantity must be positive: {quantity}")
        self.quantity = quantity


class InsufficientAvailableStockError(ReservationError):
    """Raised when a reservation exceeds the currently available stock."""

    def __init__(self, requested: int, available: int) -> None:
        super().__init__(
            f"Insufficient available stock: requested={requested}, "
            f"available={available}"
        )
        self.requested = requested
        self.available = available


class ReservationService:
    """Manages reservations and computes availability from inventory.

    Availability is derived as ``physical_stock - active_reserved_quantity``.
    Physical stock is owned by :class:`InventoryService`; this service never
    mutates it and only affects availability through active reservations.
    """

    def __init__(self, session: Session) -> None:
        self._session = session
        self._reservations = ReservationRepository(session)
        self._inventory = InventoryService(session)

    def create_reservation(
        self,
        product_id: uuid.UUID,
        warehouse_id: uuid.UUID,
        quantity: int,
        reference: str,
    ) -> Reservation:
        """Reserve ``quantity`` units if enough stock is available."""
        self._inventory.require_product(product_id)
        self._inventory.require_warehouse(warehouse_id)
        if quantity <= 0:
            raise InvalidReservationQuantityError(quantity)

        available = self.get_available_stock(product_id, warehouse_id)
        if quantity > available:
            raise InsufficientAvailableStockError(quantity, available)

        return self._reservations.add(
            Reservation(
                product_id=product_id,
                warehouse_id=warehouse_id,
                quantity=quantity,
                reference=reference,
                status=ReservationStatus.ACTIVE,
            )
        )

    def release_reservation(self, reservation_id: uuid.UUID) -> Reservation:
        """Transition an active reservation to ``RELEASED``."""
        reservation = self.require_reservation(reservation_id)
        self._ensure_active(reservation)
        reservation.status = ReservationStatus.RELEASED
        self._session.flush()
        return reservation

    def fulfill_reservation(self, reservation_id: uuid.UUID) -> Reservation:
        """Transition an active reservation to ``FULFILLED``."""
        reservation = self.require_reservation(reservation_id)
        self._ensure_active(reservation)
        reservation.status = ReservationStatus.FULFILLED
        self._session.flush()
        return reservation

    def get_reserved_quantity(
        self, product_id: uuid.UUID, warehouse_id: uuid.UUID
    ) -> int:
        """Return the total quantity held by active reservations."""
        return sum(
            reservation.quantity
            for reservation in self.get_active_reservations(
                product_id, warehouse_id
            )
        )

    def get_available_stock(
        self, product_id: uuid.UUID, warehouse_id: uuid.UUID
    ) -> int:
        """Return ``physical_stock - active_reserved_quantity``."""
        physical = self._inventory.get_stock(product_id, warehouse_id)
        reserved = self.get_reserved_quantity(product_id, warehouse_id)
        return physical - reserved

    def get_active_reservations(
        self, product_id: uuid.UUID, warehouse_id: uuid.UUID
    ) -> list[Reservation]:
        """Return active reservations for a (product, warehouse) pair."""
        return self._reservations.get_active_by_product_and_warehouse(
            product_id, warehouse_id
        )

    def require_reservation(
        self, reservation_id: uuid.UUID
    ) -> Reservation:
        """Return the reservation or raise :class:`ReservationNotFoundError`."""
        reservation = self._reservations.get(reservation_id)
        if reservation is None:
            raise ReservationNotFoundError(reservation_id)
        return reservation

    @staticmethod
    def _ensure_active(reservation: Reservation) -> None:
        if reservation.status is ReservationStatus.RELEASED:
            raise ReservationAlreadyReleasedError(reservation.id)
        if reservation.status is ReservationStatus.FULFILLED:
            raise ReservationAlreadyFulfilledError(reservation.id)
