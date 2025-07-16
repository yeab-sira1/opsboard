"""Edge-case tests for :class:`ReservationService`."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from src.services import (
    InsufficientAvailableStockError,
    InventoryService,
    ReservationAlreadyFulfilledError,
    ReservationAlreadyReleasedError,
    ReservationNotFoundError,
    ReservationService,
)


@pytest.fixture
def inventory(session: Session) -> InventoryService:
    return InventoryService(session)


@pytest.fixture
def reservations(session: Session) -> ReservationService:
    return ReservationService(session)


def test_reservations_are_isolated_per_warehouse(
    inventory: InventoryService, reservations: ReservationService
) -> None:
    product = inventory.add_product(sku="SKU-1", name="Widget", unit="pcs")
    wh1 = inventory.create_warehouse(code="WH-1", name="Main", location="B")
    wh2 = inventory.create_warehouse(code="WH-2", name="Annex", location="M")
    inventory.set_stock(product.id, wh1.id, 10)
    inventory.set_stock(product.id, wh2.id, 10)

    reservations.create_reservation(product.id, wh1.id, 4, "ORD-1")

    assert reservations.get_available_stock(product.id, wh1.id) == 6
    assert reservations.get_available_stock(product.id, wh2.id) == 10
    assert reservations.get_reserved_quantity(product.id, wh2.id) == 0


def test_release_then_reserve_again_uses_freed_stock(
    inventory: InventoryService, reservations: ReservationService
) -> None:
    product = inventory.add_product(sku="SKU-1", name="Widget", unit="pcs")
    warehouse = inventory.create_warehouse(
        code="WH-1", name="Main", location="B"
    )
    inventory.set_stock(product.id, warehouse.id, 5)

    first = reservations.create_reservation(product.id, warehouse.id, 5, "A")
    assert reservations.get_available_stock(product.id, warehouse.id) == 0
    with pytest.raises(InsufficientAvailableStockError):
        reservations.create_reservation(product.id, warehouse.id, 1, "B")

    reservations.release_reservation(first.id)
    assert reservations.get_available_stock(product.id, warehouse.id) == 5
    reservations.create_reservation(product.id, warehouse.id, 5, "C")
    assert reservations.get_available_stock(product.id, warehouse.id) == 0


def test_reserve_exact_available_then_one_more_fails(
    inventory: InventoryService, reservations: ReservationService
) -> None:
    product = inventory.add_product(sku="SKU-1", name="Widget", unit="pcs")
    warehouse = inventory.create_warehouse(
        code="WH-1", name="Main", location="B"
    )
    inventory.set_stock(product.id, warehouse.id, 5)

    reservations.create_reservation(product.id, warehouse.id, 5, "A")
    with pytest.raises(InsufficientAvailableStockError):
        reservations.create_reservation(product.id, warehouse.id, 1, "B")


def test_cross_state_transitions_raise(
    inventory: InventoryService, reservations: ReservationService
) -> None:
    product = inventory.add_product(sku="SKU-1", name="Widget", unit="pcs")
    warehouse = inventory.create_warehouse(
        code="WH-1", name="Main", location="B"
    )
    inventory.set_stock(product.id, warehouse.id, 10)

    released = reservations.create_reservation(product.id, warehouse.id, 2, "A")
    reservations.release_reservation(released.id)
    with pytest.raises(ReservationAlreadyReleasedError):
        reservations.fulfill_reservation(released.id)

    fulfilled = reservations.create_reservation(
        product.id, warehouse.id, 2, "B"
    )
    reservations.fulfill_reservation(fulfilled.id)
    with pytest.raises(ReservationAlreadyFulfilledError):
        reservations.release_reservation(fulfilled.id)


def test_fulfill_unknown_reservation_raises(
    reservations: ReservationService,
) -> None:
    with pytest.raises(ReservationNotFoundError):
        reservations.fulfill_reservation(uuid.uuid4())


def test_no_physical_stock_means_zero_availability(
    inventory: InventoryService, reservations: ReservationService
) -> None:
    product = inventory.add_product(sku="SKU-1", name="Widget", unit="pcs")
    warehouse = inventory.create_warehouse(
        code="WH-1", name="Main", location="B"
    )

    assert reservations.get_available_stock(product.id, warehouse.id) == 0
    with pytest.raises(InsufficientAvailableStockError):
        reservations.create_reservation(product.id, warehouse.id, 1, "A")
