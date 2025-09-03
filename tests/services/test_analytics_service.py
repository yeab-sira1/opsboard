"""Tests for :class:`AnalyticsService` summaries and snapshot generation."""

from __future__ import annotations

import uuid
from datetime import date

import pytest
from sqlalchemy.orm import Session

from src.models import OrderStatus, ReservationStatus
from src.services import (
    AnalyticsService,
    InventoryService,
    OrderLine,
    OrderService,
    ReservationService,
    SnapshotAlreadyExistsError,
    SnapshotNotFoundError,
)


@pytest.fixture
def env(
    session: Session,
) -> tuple[
    InventoryService, ReservationService, OrderService, AnalyticsService
]:
    return (
        InventoryService(session),
        ReservationService(session),
        OrderService(session),
        AnalyticsService(session),
    )


def _setup(
    inventory: InventoryService, reservations: ReservationService
) -> tuple[uuid.UUID, uuid.UUID]:
    product = inventory.add_product(sku="SKU-1", name="Widget", unit="pcs")
    warehouse = inventory.create_warehouse(
        code="WH-1", name="Main", location="Berlin"
    )
    inventory.set_stock(product.id, warehouse.id, 10)
    reservations.create_reservation(product.id, warehouse.id, 4, "ORD-1")
    return product.id, warehouse.id


def test_inventory_summary(env) -> None:
    inventory, reservations, _, analytics = env
    product_id, warehouse_id = _setup(inventory, reservations)

    summary = analytics.get_inventory_summary()
    assert len(summary) == 1
    row = summary[0]
    assert row.product_id == product_id
    assert row.warehouse_id == warehouse_id
    assert row.physical_stock == 10
    assert row.reserved_quantity == 4
    assert row.available_stock == 6


def test_order_summary_counts_by_status(env) -> None:
    inventory, reservations, orders, analytics = env
    product_id, warehouse_id = _setup(inventory, reservations)
    r2 = reservations.create_reservation(product_id, warehouse_id, 2, "ORD-2")
    r3 = reservations.create_reservation(product_id, warehouse_id, 1, "ORD-3")

    pending = orders.create_order(
        "ORD-2", [OrderLine(r2.id, 2)]
    )  # stays PENDING
    confirmed = orders.create_order("ORD-3", [OrderLine(r3.id, 1)])
    orders.confirm_order(confirmed.id)

    summary = analytics.get_order_summary()
    assert summary[OrderStatus.PENDING] == 1
    assert summary[OrderStatus.CONFIRMED] == 1
    assert summary[OrderStatus.COMPLETED] == 0
    assert summary[OrderStatus.CANCELLED] == 0
    assert pending.status is OrderStatus.PENDING


def test_reservation_summary_counts_by_status(env) -> None:
    inventory, reservations, _, analytics = env
    product_id, warehouse_id = _setup(inventory, reservations)
    to_release = reservations.create_reservation(
        product_id, warehouse_id, 1, "R"
    )
    to_fulfill = reservations.create_reservation(
        product_id, warehouse_id, 1, "F"
    )
    reservations.release_reservation(to_release.id)
    reservations.fulfill_reservation(to_fulfill.id)

    summary = analytics.get_reservation_summary()
    assert summary[ReservationStatus.ACTIVE] == 1
    assert summary[ReservationStatus.RELEASED] == 1
    assert summary[ReservationStatus.FULFILLED] == 1


def test_generate_and_read_snapshot(env) -> None:
    inventory, reservations, _, analytics = env
    product_id, warehouse_id = _setup(inventory, reservations)

    created = analytics.generate_daily_snapshot(date(2026, 1, 1))
    assert len(created) == 1

    snapshot = analytics.get_snapshot(
        date(2026, 1, 1), product_id, warehouse_id
    )
    assert snapshot.physical_stock == 10
    assert snapshot.reserved_quantity == 4
    assert snapshot.available_stock == 6
    assert len(analytics.get_snapshots_by_date(date(2026, 1, 1))) == 1


def test_duplicate_snapshot_for_date_raises(env) -> None:
    inventory, reservations, _, analytics = env
    _setup(inventory, reservations)

    analytics.generate_daily_snapshot(date(2026, 1, 1))
    with pytest.raises(SnapshotAlreadyExistsError):
        analytics.generate_daily_snapshot(date(2026, 1, 1))


def test_get_missing_snapshot_raises(env) -> None:
    _, _, _, analytics = env
    with pytest.raises(SnapshotNotFoundError):
        analytics.get_snapshot(date(2026, 1, 1), uuid.uuid4(), uuid.uuid4())
