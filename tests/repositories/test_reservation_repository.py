"""Tests for :class:`ReservationRepository`."""

from __future__ import annotations

from sqlalchemy.orm import Session

from src.models import Product, Reservation, ReservationStatus, Warehouse
from src.repositories import ReservationRepository


def _seed(session: Session) -> tuple[Product, Warehouse]:
    product = Product(sku="SKU-1", name="Widget", unit="pcs")
    warehouse = Warehouse(code="WH-1", name="Main", location="Berlin")
    session.add_all([product, warehouse])
    session.flush()
    return product, warehouse


def test_get_active_by_product_and_warehouse(session: Session) -> None:
    product, warehouse = _seed(session)
    repo = ReservationRepository(session)

    active = repo.add(
        Reservation(
            product_id=product.id,
            warehouse_id=warehouse.id,
            quantity=2,
            reference="A",
        )
    )
    repo.add(
        Reservation(
            product_id=product.id,
            warehouse_id=warehouse.id,
            quantity=3,
            reference="B",
            status=ReservationStatus.RELEASED,
        )
    )

    results = repo.get_active_by_product_and_warehouse(
        product.id, warehouse.id
    )
    assert [r.id for r in results] == [active.id]


def test_get_by_reference_and_active_by_reference(session: Session) -> None:
    product, warehouse = _seed(session)
    repo = ReservationRepository(session)

    repo.add(
        Reservation(
            product_id=product.id,
            warehouse_id=warehouse.id,
            quantity=1,
            reference="SHARED",
        )
    )
    repo.add(
        Reservation(
            product_id=product.id,
            warehouse_id=warehouse.id,
            quantity=4,
            reference="SHARED",
            status=ReservationStatus.FULFILLED,
        )
    )

    assert len(repo.get_by_reference("SHARED")) == 2
    active = repo.get_active_by_reference("SHARED")
    assert len(active) == 1
    assert active[0].status is ReservationStatus.ACTIVE
    assert repo.get_by_reference("missing") == []
