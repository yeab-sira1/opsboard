"""Tests for :class:`OrderService` and its reservation integration."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from src.models import OrderStatus, ReservationStatus
from src.services import (
    DuplicateOrderReferenceError,
    EmptyOrderError,
    InactiveReservationError,
    InvalidOrderStateError,
    InventoryService,
    OrderLine,
    OrderNotFoundError,
    OrderQuantityMismatchError,
    OrderService,
    ReservationService,
)


@pytest.fixture
def env(
    session: Session,
) -> tuple[InventoryService, ReservationService, OrderService]:
    return (
        InventoryService(session),
        ReservationService(session),
        OrderService(session),
    )


def _stocked_product(
    inventory: InventoryService, quantity: int = 10
) -> tuple[uuid.UUID, uuid.UUID]:
    product = inventory.add_product(sku="SKU-1", name="Widget", unit="pcs")
    warehouse = inventory.create_warehouse(
        code="WH-1", name="Main", location="Berlin"
    )
    inventory.set_stock(product.id, warehouse.id, quantity)
    return product.id, warehouse.id


def test_create_order_starts_pending(env) -> None:
    inventory, reservations, orders = env
    product_id, warehouse_id = _stocked_product(inventory)
    reservation = reservations.create_reservation(
        product_id, warehouse_id, 4, "ORD-1"
    )

    order = orders.create_order(
        "ORD-1", [OrderLine(reservation.id, 4)]
    )
    assert order.status is OrderStatus.PENDING
    assert len(order.items) == 1


def test_duplicate_reference_rejected(env) -> None:
    inventory, reservations, orders = env
    product_id, warehouse_id = _stocked_product(inventory)
    r1 = reservations.create_reservation(product_id, warehouse_id, 2, "A")
    r2 = reservations.create_reservation(product_id, warehouse_id, 2, "B")

    orders.create_order("DUP", [OrderLine(r1.id, 2)])
    with pytest.raises(DuplicateOrderReferenceError):
        orders.create_order("DUP", [OrderLine(r2.id, 2)])


def test_create_order_requires_matching_quantity(env) -> None:
    inventory, reservations, orders = env
    product_id, warehouse_id = _stocked_product(inventory)
    reservation = reservations.create_reservation(
        product_id, warehouse_id, 4, "ORD-1"
    )

    with pytest.raises(OrderQuantityMismatchError):
        orders.create_order("ORD-1", [OrderLine(reservation.id, 3)])


def test_create_order_requires_active_reservation(env) -> None:
    inventory, reservations, orders = env
    product_id, warehouse_id = _stocked_product(inventory)
    reservation = reservations.create_reservation(
        product_id, warehouse_id, 4, "ORD-1"
    )
    reservations.release_reservation(reservation.id)

    with pytest.raises(InactiveReservationError):
        orders.create_order("ORD-1", [OrderLine(reservation.id, 4)])


def test_empty_order_rejected(env) -> None:
    _, _, orders = env
    with pytest.raises(EmptyOrderError):
        orders.create_order("ORD-1", [])


def test_confirm_then_complete_fulfills_reservations(env) -> None:
    inventory, reservations, orders = env
    product_id, warehouse_id = _stocked_product(inventory, 10)
    reservation = reservations.create_reservation(
        product_id, warehouse_id, 4, "ORD-1"
    )
    order = orders.create_order("ORD-1", [OrderLine(reservation.id, 4)])

    orders.confirm_order(order.id)
    assert orders.get_order(order.id).status is OrderStatus.CONFIRMED

    orders.complete_order(order.id)
    assert orders.get_order(order.id).status is OrderStatus.COMPLETED
    assert (
        reservations.require_reservation(reservation.id).status
        is ReservationStatus.FULFILLED
    )
    # Physical stock is left unchanged.
    assert inventory.get_stock(product_id, warehouse_id) == 10


def test_cancel_releases_reservations_and_restores_availability(env) -> None:
    inventory, reservations, orders = env
    product_id, warehouse_id = _stocked_product(inventory, 10)
    reservation = reservations.create_reservation(
        product_id, warehouse_id, 4, "ORD-1"
    )
    order = orders.create_order("ORD-1", [OrderLine(reservation.id, 4)])

    assert reservations.get_available_stock(product_id, warehouse_id) == 6
    orders.cancel_order(order.id)

    assert order.status is OrderStatus.CANCELLED
    assert (
        reservations.require_reservation(reservation.id).status
        is ReservationStatus.RELEASED
    )
    assert reservations.get_available_stock(product_id, warehouse_id) == 10


def test_invalid_transitions_raise(env) -> None:
    inventory, reservations, orders = env
    product_id, warehouse_id = _stocked_product(inventory)
    reservation = reservations.create_reservation(
        product_id, warehouse_id, 2, "ORD-1"
    )
    order = orders.create_order("ORD-1", [OrderLine(reservation.id, 2)])

    # Cannot complete a PENDING order (must be CONFIRMED first).
    with pytest.raises(InvalidOrderStateError):
        orders.complete_order(order.id)


def test_get_order_and_by_status(env) -> None:
    inventory, reservations, orders = env
    product_id, warehouse_id = _stocked_product(inventory)
    reservation = reservations.create_reservation(
        product_id, warehouse_id, 2, "ORD-1"
    )
    order = orders.create_order("ORD-1", [OrderLine(reservation.id, 2)])

    assert orders.get_order(order.id) is order
    assert orders.get_orders_by_status(OrderStatus.PENDING) == [order]
    with pytest.raises(OrderNotFoundError):
        orders.get_order(uuid.uuid4())
