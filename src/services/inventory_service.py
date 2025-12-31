"""Inventory service: products, warehouses, and stock-level management."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from src.models.product import Product
from src.models.stock_record import StockRecord
from src.models.warehouse import Warehouse
from src.repositories import (
    ProductRepository,
    StockRecordRepository,
    WarehouseRepository,
)


class InventoryError(Exception):
    """Base class for inventory-related errors."""


class ProductNotFoundError(InventoryError):
    """Raised when a referenced product does not exist."""

    def __init__(self, product_id: uuid.UUID) -> None:
        super().__init__(f"Product not found: {product_id}")
        self.product_id = product_id


class WarehouseNotFoundError(InventoryError):
    """Raised when a referenced warehouse does not exist."""

    def __init__(self, warehouse_id: uuid.UUID) -> None:
        super().__init__(f"Warehouse not found: {warehouse_id}")
        self.warehouse_id = warehouse_id


class NegativeStockError(InventoryError):
    """Raised when an operation would drive stock below zero."""

    def __init__(self, current: int, delta: int) -> None:
        super().__init__(
            f"Operation would make stock negative: current={current}, "
            f"delta={delta}"
        )
        self.current = current
        self.delta = delta


class InventoryService:
    """Coordinates inventory repositories to manage stock levels.

    All stock operations keep on-hand quantities non-negative and raise a
    descriptive :class:`InventoryError` subclass on invalid input.
    """

    def __init__(self, session: Session) -> None:
        self._session = session
        self._products = ProductRepository(session)
        self._warehouses = WarehouseRepository(session)
        self._stock = StockRecordRepository(session)

    def add_product(
        self,
        sku: str,
        name: str,
        unit: str,
        description: str | None = None,
    ) -> Product:
        """Create and persist a new product."""
        return self._products.add(
            Product(sku=sku, name=name, unit=unit, description=description)
        )

    def create_warehouse(
        self, code: str, name: str, location: str
    ) -> Warehouse:
        """Create and persist a new warehouse."""
        return self._warehouses.add(
            Warehouse(code=code, name=name, location=location)
        )

    def get_product_by_sku(self, sku: str) -> Product | None:
        """Return the product with ``sku`` or ``None`` if absent."""
        return self._products.get_by_sku(sku)

    def get_warehouse_by_code(self, code: str) -> Warehouse | None:
        """Return the warehouse with ``code`` or ``None`` if absent."""
        return self._warehouses.get_by_code(code)

    def set_stock(
        self,
        product_id: uuid.UUID,
        warehouse_id: uuid.UUID,
        quantity: int,
    ) -> StockRecord:
        """Set the absolute on-hand quantity for a product/warehouse pair."""
        if quantity < 0:
            raise NegativeStockError(current=0, delta=quantity)
        self.require_product(product_id)
        self.require_warehouse(warehouse_id)

        record = self._stock.get_by_product_and_warehouse(
            product_id, warehouse_id
        )
        if record is None:
            return self._stock.add(
                StockRecord(
                    product_id=product_id,
                    warehouse_id=warehouse_id,
                    quantity=quantity,
                )
            )
        record.quantity = quantity
        self._session.flush()
        return record

    def adjust_stock(
        self,
        product_id: uuid.UUID,
        warehouse_id: uuid.UUID,
        delta: int,
    ) -> StockRecord:
        """Apply a relative change to the on-hand quantity.

        ``delta`` may be negative to consume stock; the resulting quantity must
        remain non-negative.
        """
        self.require_product(product_id)
        self.require_warehouse(warehouse_id)

        record = self._stock.get_by_product_and_warehouse(
            product_id, warehouse_id
        )
        current = record.quantity if record is not None else 0
        new_quantity = current + delta
        if new_quantity < 0:
            raise NegativeStockError(current=current, delta=delta)

        if record is None:
            return self._stock.add(
                StockRecord(
                    product_id=product_id,
                    warehouse_id=warehouse_id,
                    quantity=new_quantity,
                )
            )
        record.quantity = new_quantity
        self._session.flush()
        return record

    def get_stock(
        self, product_id: uuid.UUID, warehouse_id: uuid.UUID
    ) -> int:
        """Return the on-hand quantity, or ``0`` if no record exists."""
        record = self._stock.get_by_product_and_warehouse(
            product_id, warehouse_id
        )
        return record.quantity if record is not None else 0

    def require_product(self, product_id: uuid.UUID) -> Product:
        """Return the product or raise :class:`ProductNotFoundError`."""
        product = self._products.get(product_id)
        if product is None:
            raise ProductNotFoundError(product_id)
        return product

    def require_warehouse(self, warehouse_id: uuid.UUID) -> Warehouse:
        """Return the warehouse or raise :class:`WarehouseNotFoundError`."""
        warehouse = self._warehouses.get(warehouse_id)
        if warehouse is None:
            raise WarehouseNotFoundError(warehouse_id)
        return warehouse
