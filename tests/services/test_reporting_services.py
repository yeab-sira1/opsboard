"""Tests for :class:`DashboardService` and :class:`ExportService`."""

from __future__ import annotations

import csv
import io
from datetime import date

import pytest
from sqlalchemy.orm import Session

from src.models import OrderStatus, ReservationStatus
from src.services import (
    AnalyticsService,
    DashboardService,
    ExportService,
    InventoryService,
    ReservationService,
)


@pytest.fixture
def env(
    session: Session,
) -> tuple[
    InventoryService,
    ReservationService,
    AnalyticsService,
    DashboardService,
    ExportService,
]:
    return (
        InventoryService(session),
        ReservationService(session),
        AnalyticsService(session),
        DashboardService(session),
        ExportService(session),
    )


def _setup(
    inventory: InventoryService, reservations: ReservationService
) -> tuple:
    product = inventory.add_product(sku="SKU-1", name="Widget", unit="pcs")
    warehouse = inventory.create_warehouse(
        code="WH-1", name="Main", location="Berlin"
    )
    inventory.set_stock(product.id, warehouse.id, 10)
    reservations.create_reservation(product.id, warehouse.id, 4, "ORD-1")
    return product.id, warehouse.id


def _parse(csv_text: str) -> list[list[str]]:
    return list(csv.reader(io.StringIO(csv_text)))


def test_inventory_dashboard(env) -> None:
    inventory, reservations, _, dashboard, _ = env
    _setup(inventory, reservations)

    view = dashboard.get_inventory_dashboard()
    assert len(view.rows) == 1
    assert view.total_physical == 10
    assert view.total_reserved == 4
    assert view.total_available == 6


def test_order_and_reservation_dashboards(env) -> None:
    inventory, reservations, _, dashboard, _ = env
    _setup(inventory, reservations)

    reservation_view = dashboard.get_reservation_dashboard()
    assert reservation_view.counts[ReservationStatus.ACTIVE] == 1
    assert reservation_view.total_reservations == 1

    order_view = dashboard.get_order_dashboard()
    assert order_view.total_orders == 0
    assert order_view.counts[OrderStatus.PENDING] == 0


def test_snapshot_dashboard(env) -> None:
    inventory, reservations, analytics, dashboard, _ = env
    _setup(inventory, reservations)
    analytics.generate_daily_snapshot(date(2026, 1, 1))

    view = dashboard.get_snapshot_dashboard(date(2026, 1, 1))
    assert view.snapshot_date == date(2026, 1, 1)
    assert len(view.rows) == 1
    assert view.total_available == 6


def test_inventory_csv_export(env) -> None:
    inventory, reservations, _, _, export = env
    product_id, warehouse_id = _setup(inventory, reservations)

    rows = _parse(export.export_inventory_summary_csv())
    assert rows[0] == [
        "product_id",
        "warehouse_id",
        "physical_stock",
        "reserved_quantity",
        "available_stock",
    ]
    assert rows[1] == [str(product_id), str(warehouse_id), "10", "4", "6"]


def test_order_csv_export(env) -> None:
    inventory, reservations, _, _, export = env
    _setup(inventory, reservations)

    rows = _parse(export.export_order_summary_csv())
    assert rows[0] == ["status", "count"]
    statuses = [row[0] for row in rows[1:]]
    assert statuses == [status.value for status in OrderStatus]


def test_reservation_csv_export(env) -> None:
    inventory, reservations, _, _, export = env
    _setup(inventory, reservations)

    rows = _parse(export.export_reservation_summary_csv())
    assert rows[0] == ["status", "count"]
    counts = {row[0]: row[1] for row in rows[1:]}
    assert counts[ReservationStatus.ACTIVE.value] == "1"


def test_snapshot_csv_export(env) -> None:
    inventory, reservations, analytics, _, export = env
    product_id, warehouse_id = _setup(inventory, reservations)
    analytics.generate_daily_snapshot(date(2026, 1, 1))

    rows = _parse(export.export_daily_snapshot_csv(date(2026, 1, 1)))
    assert rows[0][0] == "snapshot_date"
    assert rows[1] == [
        "2026-01-01",
        str(product_id),
        str(warehouse_id),
        "10",
        "4",
        "6",
    ]
