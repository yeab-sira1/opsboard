"""Tests for :class:`DailyInventorySnapshotRepository`."""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from src.models import DailyInventorySnapshot, Product, Warehouse
from src.repositories import DailyInventorySnapshotRepository


def _seed(session: Session) -> tuple[Product, Product, Warehouse, Warehouse]:
    p1 = Product(sku="SKU-1", name="Widget", unit="pcs")
    p2 = Product(sku="SKU-2", name="Gadget", unit="pcs")
    w1 = Warehouse(code="WH-1", name="Main", location="Berlin")
    w2 = Warehouse(code="WH-2", name="Annex", location="Munich")
    session.add_all([p1, p2, w1, w2])
    session.flush()
    return p1, p2, w1, w2


def _snapshot(
    snapshot_date: date, product_id, warehouse_id
) -> DailyInventorySnapshot:
    return DailyInventorySnapshot(
        snapshot_date=snapshot_date,
        product_id=product_id,
        warehouse_id=warehouse_id,
        physical_stock=10,
        reserved_quantity=0,
        available_stock=10,
    )


def test_get_by_date_product_and_warehouse(session: Session) -> None:
    p1, p2, w1, w2 = _seed(session)
    repo = DailyInventorySnapshotRepository(session)

    repo.add(_snapshot(date(2026, 1, 1), p1.id, w1.id))
    repo.add(_snapshot(date(2026, 1, 1), p2.id, w2.id))
    repo.add(_snapshot(date(2026, 1, 2), p1.id, w1.id))

    assert len(repo.get_by_date(date(2026, 1, 1))) == 2
    assert len(repo.get_by_date(date(2026, 1, 2))) == 1
    assert repo.get_by_date(date(2026, 1, 3)) == []

    assert len(repo.get_by_product(p1.id)) == 2
    assert len(repo.get_by_product(p2.id)) == 1

    assert len(repo.get_by_warehouse(w1.id)) == 2
    assert len(repo.get_by_warehouse(w2.id)) == 1
