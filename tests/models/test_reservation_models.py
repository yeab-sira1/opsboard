"""Tests for the reservation ORM model and relationships."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.models import Product, Reservation, ReservationStatus, Warehouse


def _product_and_warehouse(session: Session) -> tuple[Product, Warehouse]:
    product = Product(sku="SKU-1", name="Widget", unit="pcs")
    warehouse = Warehouse(code="WH-1", name="Main", location="Berlin")
    session.add_all([product, warehouse])
    session.flush()
    return product, warehouse


def test_create_reservation_defaults_to_active(session: Session) -> None:
    product, warehouse = _product_and_warehouse(session)
    reservation = Reservation(
        product_id=product.id,
        warehouse_id=warehouse.id,
        quantity=5,
        reference="ORD-1",
    )
    session.add(reservation)
    session.flush()

    assert isinstance(reservation.id, uuid.UUID)
    assert reservation.status is ReservationStatus.ACTIVE


def test_reservation_relationships(session: Session) -> None:
    product, warehouse = _product_and_warehouse(session)
    reservation = Reservation(
        product=product,
        warehouse=warehouse,
        quantity=3,
        reference="ORD-1",
    )
    session.add(reservation)
    session.flush()

    assert reservation.product is product
    assert reservation.warehouse is warehouse


def test_reference_is_not_unique(session: Session) -> None:
    product, warehouse = _product_and_warehouse(session)
    session.add_all(
        [
            Reservation(
                product_id=product.id,
                warehouse_id=warehouse.id,
                quantity=1,
                reference="SHARED",
            ),
            Reservation(
                product_id=product.id,
                warehouse_id=warehouse.id,
                quantity=2,
                reference="SHARED",
            ),
        ]
    )
    session.flush()

    rows = session.query(Reservation).filter_by(reference="SHARED").all()
    assert len(rows) == 2


def test_non_positive_quantity_rejected(session: Session) -> None:
    product, warehouse = _product_and_warehouse(session)
    session.add(
        Reservation(
            product_id=product.id,
            warehouse_id=warehouse.id,
            quantity=0,
            reference="ORD-1",
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()
    session.rollback()
