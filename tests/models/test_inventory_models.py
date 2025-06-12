"""Tests for the inventory ORM models, relationships, and constraints."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.models import Product, StockRecord, Warehouse


def _product(session: Session, sku: str = "SKU-1") -> Product:
    product = Product(sku=sku, name="Widget", unit="pcs")
    session.add(product)
    session.flush()
    return product


def _warehouse(session: Session, code: str = "WH-1") -> Warehouse:
    warehouse = Warehouse(code=code, name="Main", location="Berlin")
    session.add(warehouse)
    session.flush()
    return warehouse


def test_create_product(session: Session) -> None:
    product = _product(session)
    assert isinstance(product.id, uuid.UUID)
    assert product.description is None
    assert product.stock_records == []


def test_create_warehouse(session: Session) -> None:
    warehouse = _warehouse(session)
    assert isinstance(warehouse.id, uuid.UUID)
    assert warehouse.stock_records == []


def test_stock_record_relationships(session: Session) -> None:
    product = _product(session)
    warehouse = _warehouse(session)
    record = StockRecord(product=product, warehouse=warehouse, quantity=5)
    session.add(record)
    session.flush()

    assert record.product is product
    assert record.warehouse is warehouse
    assert record in product.stock_records
    assert record in warehouse.stock_records


def test_product_sku_is_unique(session: Session) -> None:
    _product(session, sku="DUP")
    session.add(Product(sku="DUP", name="Other", unit="pcs"))
    with pytest.raises(IntegrityError):
        session.flush()
    session.rollback()


def test_warehouse_code_is_unique(session: Session) -> None:
    _warehouse(session, code="DUP")
    session.add(Warehouse(code="DUP", name="Other", location="Munich"))
    with pytest.raises(IntegrityError):
        session.flush()
    session.rollback()


def test_stock_record_pair_is_unique(session: Session) -> None:
    product = _product(session)
    warehouse = _warehouse(session)
    session.add(
        StockRecord(product_id=product.id, warehouse_id=warehouse.id, quantity=1)
    )
    session.flush()
    session.add(
        StockRecord(product_id=product.id, warehouse_id=warehouse.id, quantity=2)
    )
    with pytest.raises(IntegrityError):
        session.flush()
    session.rollback()
