"""Tests for :class:`InventoryService`."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from src.services import (
    InventoryService,
    NegativeStockError,
    ProductNotFoundError,
    WarehouseNotFoundError,
)


@pytest.fixture
def service(session: Session) -> InventoryService:
    return InventoryService(session)


def test_add_product_and_create_warehouse(service: InventoryService) -> None:
    product = service.add_product(sku="SKU-1", name="Widget", unit="pcs")
    warehouse = service.create_warehouse(
        code="WH-1", name="Main", location="Berlin"
    )
    assert isinstance(product.id, uuid.UUID)
    assert isinstance(warehouse.id, uuid.UUID)


def test_set_stock_creates_then_overwrites(service: InventoryService) -> None:
    product = service.add_product(sku="SKU-1", name="Widget", unit="pcs")
    warehouse = service.create_warehouse(
        code="WH-1", name="Main", location="Berlin"
    )

    assert service.get_stock(product.id, warehouse.id) == 0

    service.set_stock(product.id, warehouse.id, 10)
    assert service.get_stock(product.id, warehouse.id) == 10

    service.set_stock(product.id, warehouse.id, 3)
    assert service.get_stock(product.id, warehouse.id) == 3


def test_adjust_stock_increase_and_decrease(
    service: InventoryService,
) -> None:
    product = service.add_product(sku="SKU-1", name="Widget", unit="pcs")
    warehouse = service.create_warehouse(
        code="WH-1", name="Main", location="Berlin"
    )

    service.adjust_stock(product.id, warehouse.id, 8)
    assert service.get_stock(product.id, warehouse.id) == 8

    service.adjust_stock(product.id, warehouse.id, -5)
    assert service.get_stock(product.id, warehouse.id) == 3


def test_set_stock_rejects_negative(service: InventoryService) -> None:
    product = service.add_product(sku="SKU-1", name="Widget", unit="pcs")
    warehouse = service.create_warehouse(
        code="WH-1", name="Main", location="Berlin"
    )
    with pytest.raises(NegativeStockError):
        service.set_stock(product.id, warehouse.id, -1)


def test_adjust_stock_cannot_go_below_zero(service: InventoryService) -> None:
    product = service.add_product(sku="SKU-1", name="Widget", unit="pcs")
    warehouse = service.create_warehouse(
        code="WH-1", name="Main", location="Berlin"
    )
    service.set_stock(product.id, warehouse.id, 2)

    with pytest.raises(NegativeStockError):
        service.adjust_stock(product.id, warehouse.id, -5)
    assert service.get_stock(product.id, warehouse.id) == 2


def test_operations_require_existing_entities(
    service: InventoryService,
) -> None:
    product = service.add_product(sku="SKU-1", name="Widget", unit="pcs")
    warehouse = service.create_warehouse(
        code="WH-1", name="Main", location="Berlin"
    )

    with pytest.raises(ProductNotFoundError):
        service.set_stock(uuid.uuid4(), warehouse.id, 1)
    with pytest.raises(WarehouseNotFoundError):
        service.set_stock(product.id, uuid.uuid4(), 1)
