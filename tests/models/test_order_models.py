"""Tests for the order ORM models, relationships, and constraints."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.models import (
    Order,
    OrderItem,
    OrderStatus,
    Product,
    Reservation,
    Warehouse,
)


def _reservation(session: Session, quantity: int = 5) -> Reservation:
    product = Product(sku="SKU-1", name="Widget", unit="pcs")
    warehouse = Warehouse(code="WH-1", name="Main", location="Berlin")
    session.add_all([product, warehouse])
    session.flush()
    reservation = Reservation(
        product_id=product.id,
        warehouse_id=warehouse.id,
        quantity=quantity,
        reference="ORD-1",
    )
    session.add(reservation)
    session.flush()
    return reservation


def test_order_defaults_to_pending(session: Session) -> None:
    order = Order(reference="ORD-1")
    session.add(order)
    session.flush()

    assert isinstance(order.id, uuid.UUID)
    assert order.status is OrderStatus.PENDING
    assert order.items == []


def test_order_reference_is_unique(session: Session) -> None:
    session.add(Order(reference="DUP"))
    session.flush()
    session.add(Order(reference="DUP"))
    with pytest.raises(IntegrityError):
        session.flush()
    session.rollback()


def test_order_item_relationships(session: Session) -> None:
    reservation = _reservation(session)
    order = Order(reference="ORD-1")
    item = OrderItem(reservation=reservation, quantity=5)
    order.items.append(item)
    session.add(order)
    session.flush()

    assert item.order is order
    assert item.reservation is reservation
    assert item in order.items


def test_order_item_quantity_must_be_positive(session: Session) -> None:
    reservation = _reservation(session)
    order = Order(reference="ORD-1")
    order.items.append(OrderItem(reservation_id=reservation.id, quantity=0))
    session.add(order)
    with pytest.raises(IntegrityError):
        session.flush()
    session.rollback()


def test_deleting_order_cascades_to_items(session: Session) -> None:
    reservation = _reservation(session)
    order = Order(reference="ORD-1")
    order.items.append(OrderItem(reservation_id=reservation.id, quantity=5))
    session.add(order)
    session.flush()
    assert session.query(OrderItem).count() == 1

    session.delete(order)
    session.flush()
    assert session.query(OrderItem).count() == 0
