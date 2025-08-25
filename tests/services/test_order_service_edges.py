"""Edge-case and state-transition tests for :class:`OrderService`."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from src.models import OrderStatus, ReservationStatus
from src.services import (
    InvalidOrderStateError,
    InventoryService,
    OrderLine,
    OrderService,
    ReservationService,
)


@pytest.fixture
def inventory(session: Session) -> InventoryService:
    return InventoryService(session)


@pytest.fixture
def reservations(session: Session) -> ReservationService:
    return ReservationService(session)


@pytest.fixture
def orders(session: Session) -> OrderService:
    return OrderService(session)


def _stocked_product(
    inventory: InventoryService, quantity: int = 10
) -> tuple[uuid.UUID, uuid.UUID]:
    product = inventory.add_product(sku="SKU-1", name="Widget", unit="pcs")
    warehouse = inventory.create_warehouse(
        code="WH-1", name="Main", location="Berlin"
    )
    inventory.set_stock(product.id, warehouse.id, quantity)
    return product.id, warehouse.id


def test_multi_item_order_across_warehouses(
    inventory: InventoryService,
    reservations: ReservationService,
    orders: OrderService,
) -> None:
    product = inventory.add_product(sku="SKU-1", name="Widget", unit="pcs")
    wh1 = inventory.create_warehouse(code="WH-1", name="Main", location="B")
    wh2 = inventory.create_warehouse(code="WH-2", name="Annex", location="M")
    inventory.set_stock(product.id, wh1.id, 10)
    inventory.set_stock(product.id, wh2.id, 10)

    r1 = reservations.create_reservation(product.id, wh1.id, 4, "ORD-1")
    r2 = reservations.create_reservation(product.id, wh2.id, 5, "ORD-1")
    order = orders.create_order(
        "ORD-1", [OrderLine(r1.id, 4), OrderLine(r2.id, 5)]
    )

    assert len(order.items) == 2
    assert reservations.get_available_stock(product.id, wh1.id) == 6
    assert reservations.get_available_stock(product.id, wh2.id) == 5

    orders.confirm_order(order.id)
    orders.complete_order(order.id)

    assert (
        reservations.require_reservation(r1.id).status
        is ReservationStatus.FULFILLED
    )
    assert (
        reservations.require_reservation(r2.id).status
        is ReservationStatus.FULFILLED
    )


def test_cancel_confirmed_order_releases_reservations(
    inventory: InventoryService,
    reservations: ReservationService,
    orders: OrderService,
) -> None:
    product_id, warehouse_id = _stocked_product(inventory, 10)
    reservation = reservations.create_reservation(
        product_id, warehouse_id, 4, "ORD-1"
    )
    order = orders.create_order("ORD-1", [OrderLine(reservation.id, 4)])
    orders.confirm_order(order.id)

    orders.cancel_order(order.id)
    assert order.status is OrderStatus.CANCELLED
    assert reservations.get_available_stock(product_id, warehouse_id) == 10


def test_cannot_confirm_twice(
    inventory: InventoryService,
    reservations: ReservationService,
    orders: OrderService,
) -> None:
    product_id, warehouse_id = _stocked_product(inventory)
    reservation = reservations.create_reservation(
        product_id, warehouse_id, 2, "ORD-1"
    )
    order = orders.create_order("ORD-1", [OrderLine(reservation.id, 2)])
    orders.confirm_order(order.id)

    with pytest.raises(InvalidOrderStateError):
        orders.confirm_order(order.id)


def test_cannot_cancel_completed_order(
    inventory: InventoryService,
    reservations: ReservationService,
    orders: OrderService,
) -> None:
    product_id, warehouse_id = _stocked_product(inventory)
    reservation = reservations.create_reservation(
        product_id, warehouse_id, 2, "ORD-1"
    )
    order = orders.create_order("ORD-1", [OrderLine(reservation.id, 2)])
    orders.confirm_order(order.id)
    orders.complete_order(order.id)

    with pytest.raises(InvalidOrderStateError):
        orders.cancel_order(order.id)


def test_cannot_complete_twice(
    inventory: InventoryService,
    reservations: ReservationService,
    orders: OrderService,
) -> None:
    product_id, warehouse_id = _stocked_product(inventory)
    reservation = reservations.create_reservation(
        product_id, warehouse_id, 2, "ORD-1"
    )
    order = orders.create_order("ORD-1", [OrderLine(reservation.id, 2)])
    orders.confirm_order(order.id)
    orders.complete_order(order.id)

    with pytest.raises(InvalidOrderStateError):
        orders.complete_order(order.id)


def test_cannot_confirm_cancelled_order(
    inventory: InventoryService,
    reservations: ReservationService,
    orders: OrderService,
) -> None:
    product_id, warehouse_id = _stocked_product(inventory)
    reservation = reservations.create_reservation(
        product_id, warehouse_id, 2, "ORD-1"
    )
    order = orders.create_order("ORD-1", [OrderLine(reservation.id, 2)])
    orders.cancel_order(order.id)

    with pytest.raises(InvalidOrderStateError):
        orders.confirm_order(order.id)
