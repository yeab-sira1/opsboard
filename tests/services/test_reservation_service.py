"""Tests for :class:`ReservationService`."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from src.models import ReservationStatus
from src.services import (
    InsufficientAvailableStockError,
    InvalidReservationQuantityError,
    InventoryService,
    ProductNotFoundError,
    ReservationAlreadyFulfilledError,
    ReservationAlreadyReleasedError,
    ReservationNotFoundError,
    ReservationService,
    WarehouseNotFoundError,
)


@pytest.fixture
def services(session: Session) -> tuple[InventoryService, ReservationService]:
    return InventoryService(session), ReservationService(session)


def _setup_stock(
    inventory: InventoryService, quantity: int = 10
) -> tuple[uuid.UUID, uuid.UUID]:
    product = inventory.add_product(sku="SKU-1", name="Widget", unit="pcs")
    warehouse = inventory.create_warehouse(
        code="WH-1", name="Main", location="Berlin"
    )
    inventory.set_stock(product.id, warehouse.id, quantity)
    return product.id, warehouse.id


def test_create_reservation_reduces_availability(
    services: tuple[InventoryService, ReservationService],
) -> None:
    inventory, reservations = services
    product_id, warehouse_id = _setup_stock(inventory, 10)

    assert reservations.get_available_stock(product_id, warehouse_id) == 10
    reservations.create_reservation(product_id, warehouse_id, 4, "ORD-1")

    assert reservations.get_reserved_quantity(product_id, warehouse_id) == 4
    assert reservations.get_available_stock(product_id, warehouse_id) == 6
    assert inventory.get_stock(product_id, warehouse_id) == 10  # unchanged


def test_multiple_reservations_accumulate(
    services: tuple[InventoryService, ReservationService],
) -> None:
    inventory, reservations = services
    product_id, warehouse_id = _setup_stock(inventory, 10)

    reservations.create_reservation(product_id, warehouse_id, 3, "ORD-1")
    reservations.create_reservation(product_id, warehouse_id, 2, "ORD-2")

    assert reservations.get_reserved_quantity(product_id, warehouse_id) == 5
    assert reservations.get_available_stock(product_id, warehouse_id) == 5
    assert len(
        reservations.get_active_reservations(product_id, warehouse_id)
    ) == 2


def test_reservation_rejected_when_exceeds_available(
    services: tuple[InventoryService, ReservationService],
) -> None:
    inventory, reservations = services
    product_id, warehouse_id = _setup_stock(inventory, 5)

    reservations.create_reservation(product_id, warehouse_id, 4, "ORD-1")
    with pytest.raises(InsufficientAvailableStockError):
        reservations.create_reservation(product_id, warehouse_id, 2, "ORD-2")


def test_release_frees_availability(
    services: tuple[InventoryService, ReservationService],
) -> None:
    inventory, reservations = services
    product_id, warehouse_id = _setup_stock(inventory, 10)
    reservation = reservations.create_reservation(
        product_id, warehouse_id, 4, "ORD-1"
    )

    released = reservations.release_reservation(reservation.id)
    assert released.status is ReservationStatus.RELEASED
    assert reservations.get_reserved_quantity(product_id, warehouse_id) == 0
    assert reservations.get_available_stock(product_id, warehouse_id) == 10


def test_fulfill_frees_availability(
    services: tuple[InventoryService, ReservationService],
) -> None:
    inventory, reservations = services
    product_id, warehouse_id = _setup_stock(inventory, 10)
    reservation = reservations.create_reservation(
        product_id, warehouse_id, 4, "ORD-1"
    )

    fulfilled = reservations.fulfill_reservation(reservation.id)
    assert fulfilled.status is ReservationStatus.FULFILLED
    assert reservations.get_reserved_quantity(product_id, warehouse_id) == 0
    assert inventory.get_stock(product_id, warehouse_id) == 10  # unchanged


def test_double_release_raises(
    services: tuple[InventoryService, ReservationService],
) -> None:
    inventory, reservations = services
    product_id, warehouse_id = _setup_stock(inventory, 10)
    reservation = reservations.create_reservation(
        product_id, warehouse_id, 4, "ORD-1"
    )
    reservations.release_reservation(reservation.id)

    with pytest.raises(ReservationAlreadyReleasedError):
        reservations.release_reservation(reservation.id)


def test_double_fulfill_raises(
    services: tuple[InventoryService, ReservationService],
) -> None:
    inventory, reservations = services
    product_id, warehouse_id = _setup_stock(inventory, 10)
    reservation = reservations.create_reservation(
        product_id, warehouse_id, 4, "ORD-1"
    )
    reservations.fulfill_reservation(reservation.id)

    with pytest.raises(ReservationAlreadyFulfilledError):
        reservations.fulfill_reservation(reservation.id)


def test_create_reservation_validates_inputs(
    services: tuple[InventoryService, ReservationService],
) -> None:
    inventory, reservations = services
    product_id, warehouse_id = _setup_stock(inventory, 10)

    with pytest.raises(ProductNotFoundError):
        reservations.create_reservation(uuid.uuid4(), warehouse_id, 1, "X")
    with pytest.raises(WarehouseNotFoundError):
        reservations.create_reservation(product_id, uuid.uuid4(), 1, "X")
    with pytest.raises(InvalidReservationQuantityError):
        reservations.create_reservation(product_id, warehouse_id, 0, "X")


def test_release_unknown_reservation_raises(
    services: tuple[InventoryService, ReservationService],
) -> None:
    _, reservations = services
    with pytest.raises(ReservationNotFoundError):
        reservations.release_reservation(uuid.uuid4())
