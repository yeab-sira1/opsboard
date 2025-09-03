"""Tests for the :class:`DailyInventorySnapshot` model."""

from __future__ import annotations

import uuid
from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.models import DailyInventorySnapshot, Product, Warehouse


def _product_and_warehouse(session: Session) -> tuple[Product, Warehouse]:
    product = Product(sku="SKU-1", name="Widget", unit="pcs")
    warehouse = Warehouse(code="WH-1", name="Main", location="Berlin")
    session.add_all([product, warehouse])
    session.flush()
    return product, warehouse


def test_create_snapshot(session: Session) -> None:
    product, warehouse = _product_and_warehouse(session)
    snapshot = DailyInventorySnapshot(
        snapshot_date=date(2026, 1, 1),
        product_id=product.id,
        warehouse_id=warehouse.id,
        physical_stock=10,
        reserved_quantity=4,
        available_stock=6,
    )
    session.add(snapshot)
    session.flush()

    assert isinstance(snapshot.id, uuid.UUID)
    assert snapshot.product is product
    assert snapshot.warehouse is warehouse


def test_snapshot_pair_is_unique_per_date(session: Session) -> None:
    product, warehouse = _product_and_warehouse(session)
    common = dict(
        product_id=product.id,
        warehouse_id=warehouse.id,
        physical_stock=10,
        reserved_quantity=0,
        available_stock=10,
    )
    session.add(
        DailyInventorySnapshot(snapshot_date=date(2026, 1, 1), **common)
    )
    session.flush()
    session.add(
        DailyInventorySnapshot(snapshot_date=date(2026, 1, 1), **common)
    )
    with pytest.raises(IntegrityError):
        session.flush()
    session.rollback()


def test_same_pair_allowed_on_different_dates(session: Session) -> None:
    product, warehouse = _product_and_warehouse(session)
    common = dict(
        product_id=product.id,
        warehouse_id=warehouse.id,
        physical_stock=10,
        reserved_quantity=0,
        available_stock=10,
    )
    session.add_all(
        [
            DailyInventorySnapshot(snapshot_date=date(2026, 1, 1), **common),
            DailyInventorySnapshot(snapshot_date=date(2026, 1, 2), **common),
        ]
    )
    session.flush()

    assert session.query(DailyInventorySnapshot).count() == 2
