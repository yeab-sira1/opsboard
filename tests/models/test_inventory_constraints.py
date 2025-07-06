"""Database-level constraint and cascade behavior for inventory models."""

from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.models import Product, StockRecord, Warehouse


def _product_and_warehouse(session: Session) -> tuple[Product, Warehouse]:
    product = Product(sku="SKU-1", name="Widget", unit="pcs")
    warehouse = Warehouse(code="WH-1", name="Main", location="Berlin")
    session.add_all([product, warehouse])
    session.flush()
    return product, warehouse


def test_negative_quantity_rejected_by_check_constraint(
    session: Session,
) -> None:
    product, warehouse = _product_and_warehouse(session)
    session.add(
        StockRecord(
            product_id=product.id, warehouse_id=warehouse.id, quantity=-1
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()
    session.rollback()


def test_deleting_product_cascades_to_stock_records(
    session: Session,
) -> None:
    product, warehouse = _product_and_warehouse(session)
    session.add(
        StockRecord(
            product_id=product.id, warehouse_id=warehouse.id, quantity=5
        )
    )
    session.flush()
    assert session.query(StockRecord).count() == 1

    session.delete(product)
    session.flush()
    assert session.query(StockRecord).count() == 0


def test_deleting_warehouse_cascades_to_stock_records(
    session: Session,
) -> None:
    product, warehouse = _product_and_warehouse(session)
    session.add(
        StockRecord(
            product_id=product.id, warehouse_id=warehouse.id, quantity=5
        )
    )
    session.flush()

    session.delete(warehouse)
    session.flush()
    assert session.query(StockRecord).count() == 0
