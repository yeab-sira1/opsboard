"""Edge-case tests for dashboard and export services."""

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
def inventory(session: Session) -> InventoryService:
    return InventoryService(session)


@pytest.fixture
def reservations(session: Session) -> ReservationService:
    return ReservationService(session)


@pytest.fixture
def analytics(session: Session) -> AnalyticsService:
    return AnalyticsService(session)


@pytest.fixture
def dashboard(session: Session) -> DashboardService:
    return DashboardService(session)


@pytest.fixture
def export(session: Session) -> ExportService:
    return ExportService(session)


def _parse(csv_text: str) -> list[list[str]]:
    return list(csv.reader(io.StringIO(csv_text)))


def test_empty_inventory_export_has_header_only(
    export: ExportService,
) -> None:
    rows = _parse(export.export_inventory_summary_csv())
    assert len(rows) == 1  # header, no data


def test_empty_status_exports_still_list_all_statuses(
    export: ExportService,
) -> None:
    order_rows = _parse(export.export_order_summary_csv())
    assert len(order_rows) == 1 + len(OrderStatus)
    assert all(row[1] == "0" for row in order_rows[1:])

    reservation_rows = _parse(export.export_reservation_summary_csv())
    assert len(reservation_rows) == 1 + len(ReservationStatus)


def test_empty_dashboards_have_zero_totals(
    dashboard: DashboardService,
) -> None:
    inventory_view = dashboard.get_inventory_dashboard()
    assert inventory_view.rows == []
    assert inventory_view.total_available == 0

    order_view = dashboard.get_order_dashboard()
    assert order_view.total_orders == 0


def test_inventory_export_multiple_products_and_warehouses(
    inventory: InventoryService,
    reservations: ReservationService,
    export: ExportService,
) -> None:
    p1 = inventory.add_product(sku="SKU-1", name="Widget", unit="pcs")
    p2 = inventory.add_product(sku="SKU-2", name="Gadget", unit="pcs")
    w1 = inventory.create_warehouse(code="WH-1", name="Main", location="B")
    w2 = inventory.create_warehouse(code="WH-2", name="Annex", location="M")
    inventory.set_stock(p1.id, w1.id, 10)
    inventory.set_stock(p1.id, w2.id, 5)
    inventory.set_stock(p2.id, w1.id, 8)
    reservations.create_reservation(p1.id, w1.id, 4, "A")

    rows = _parse(export.export_inventory_summary_csv())
    data = {(row[0], row[1]): row for row in rows[1:]}
    assert len(data) == 3
    assert data[(str(p1.id), str(w1.id))][4] == "6"  # available
    assert data[(str(p2.id), str(w1.id))][2] == "8"  # physical


def test_repeated_exports_are_identical(
    inventory: InventoryService,
    reservations: ReservationService,
    export: ExportService,
) -> None:
    product = inventory.add_product(sku="SKU-1", name="Widget", unit="pcs")
    warehouse = inventory.create_warehouse(
        code="WH-1", name="Main", location="B"
    )
    inventory.set_stock(product.id, warehouse.id, 10)
    reservations.create_reservation(product.id, warehouse.id, 4, "A")

    first = export.export_inventory_summary_csv()
    second = export.export_inventory_summary_csv()
    assert first == second


def test_snapshot_export_and_dashboard_empty_for_unknown_date(
    export: ExportService, dashboard: DashboardService
) -> None:
    rows = _parse(export.export_daily_snapshot_csv(date(2026, 1, 1)))
    assert len(rows) == 1  # header only

    view = dashboard.get_snapshot_dashboard(date(2026, 1, 1))
    assert view.rows == []
    assert view.total_available == 0
