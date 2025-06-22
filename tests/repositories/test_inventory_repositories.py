"""Tests for the inventory repositories."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from src.models import Product, StockRecord, Warehouse
from src.repositories import (
    ProductRepository,
    StockRecordRepository,
    WarehouseRepository,
)


def test_product_repository_crud_and_lookup(session: Session) -> None:
    repo = ProductRepository(session)

    product = repo.add(Product(sku="SKU-1", name="Widget", unit="pcs"))
    assert repo.get(product.id) is product
    assert repo.get_by_sku("SKU-1") is product
    assert repo.get_by_sku("missing") is None
    assert [p.id for p in repo.list()] == [product.id]

    repo.delete(product)
    assert repo.get(product.id) is None


def test_warehouse_repository_lookup(session: Session) -> None:
    repo = WarehouseRepository(session)

    warehouse = repo.add(Warehouse(code="WH-1", name="Main", location="Berlin"))
    assert repo.get_by_code("WH-1") is warehouse
    assert repo.get_by_code("missing") is None


def test_stock_record_repository_pair_lookup(session: Session) -> None:
    product = ProductRepository(session).add(
        Product(sku="SKU-1", name="Widget", unit="pcs")
    )
    warehouse = WarehouseRepository(session).add(
        Warehouse(code="WH-1", name="Main", location="Berlin")
    )
    repo = StockRecordRepository(session)
    record = repo.add(
        StockRecord(
            product_id=product.id, warehouse_id=warehouse.id, quantity=7
        )
    )

    found = repo.get_by_product_and_warehouse(product.id, warehouse.id)
    assert found is record
    assert (
        repo.get_by_product_and_warehouse(product.id, uuid.uuid4()) is None
    )
