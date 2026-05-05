"""End-to-end integration tests for multi-day snapshot comparison.

Tests cover snapshot creation, immutability, duplicate-date protection,
workflow-driven snapshotting, and CSV export format.
Real DB sessions. No mocks.
"""

from __future__ import annotations

import csv
import io
from datetime import date

import pytest
from sqlalchemy.orm import Session

from src.schemas import WorkflowRequest
from src.services import (
    AnalyticsService,
    DashboardService,
    ExportService,
    InventoryService,
    ReservationService,
    SnapshotAlreadyExistsError,
    WorkflowService,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

CSV_HEADER = "sku,warehouse_code,quantity\n"


def _seed(session: Session, sku: str, code: str):
    """Create and return a (product, warehouse) pair."""
    inv = InventoryService(session)
    product = inv.add_product(sku=sku, name=f"Product {sku}", unit="pcs")
    warehouse = inv.create_warehouse(
        code=code, name=f"Warehouse {code}", location="Site A"
    )
    return product, warehouse


# ---------------------------------------------------------------------------
# Test 1: two-day snapshot comparison
# ---------------------------------------------------------------------------


def test_two_day_snapshot_comparison(session: Session) -> None:
    product, warehouse = _seed(session, "SKU-SNAP", "WH-SNAP")

    inv = InventoryService(session)
    res_svc = ReservationService(session)
    analytics = AnalyticsService(session)
    export = ExportService(session)

    # Day 1 setup: stock=10, reservation=4 → available=6
    inv.set_stock(product.id, warehouse.id, 10)
    reservation = res_svc.create_reservation(
        product_id=product.id,
        warehouse_id=warehouse.id,
        quantity=4,
        reference="SNAP-DAY1",
    )
    snapshots_day1 = analytics.generate_daily_snapshot(date(2026, 1, 1))
    assert len(snapshots_day1) == 1

    # Release reservation for day 2
    res_svc.release_reservation(reservation.id)

    # Day 2 setup: stock=15, no active reservations → available=15
    inv.set_stock(product.id, warehouse.id, 15)
    snapshots_day2 = analytics.generate_daily_snapshot(date(2026, 1, 2))
    assert len(snapshots_day2) == 1

    # Verify day 1 snapshot
    snap1 = analytics.get_snapshot(date(2026, 1, 1), product.id, warehouse.id)
    assert snap1.physical_stock == 10
    assert snap1.available_stock == 6
    assert snap1.reserved_quantity == 4

    # Verify day 2 snapshot
    snap2 = analytics.get_snapshot(date(2026, 1, 2), product.id, warehouse.id)
    assert snap2.physical_stock == 15
    assert snap2.available_stock == 15
    assert snap2.reserved_quantity == 0

    # Export day 1 CSV and verify values
    csv_day1 = export.export_daily_snapshot_csv(date(2026, 1, 1))
    assert "10" in csv_day1
    assert "6" in csv_day1

    # Export day 2 CSV and verify values
    csv_day2 = export.export_daily_snapshot_csv(date(2026, 1, 2))
    assert "15" in csv_day2


# ---------------------------------------------------------------------------
# Test 2: snapshot immutability after stock changes
# ---------------------------------------------------------------------------


def test_snapshot_immutability_after_stock_changes(session: Session) -> None:
    product, warehouse = _seed(session, "SKU-SNAP", "WH-SNAP")

    inv = InventoryService(session)
    analytics = AnalyticsService(session)

    # Set stock to 10 and take snapshot
    inv.set_stock(product.id, warehouse.id, 10)
    analytics.generate_daily_snapshot(date(2026, 2, 1))

    # Overwrite stock with 20 — snapshot must not change
    inv.set_stock(product.id, warehouse.id, 20)

    snapshot = analytics.get_snapshot(date(2026, 2, 1), product.id, warehouse.id)
    assert snapshot.physical_stock == 10, (
        "Snapshot should be immutable; stock change after snapshot must not affect it"
    )


# ---------------------------------------------------------------------------
# Test 3: duplicate snapshot date fails
# ---------------------------------------------------------------------------


def test_duplicate_snapshot_date_fails(session: Session) -> None:
    product, warehouse = _seed(session, "SKU-SNAP", "WH-SNAP")

    inv = InventoryService(session)
    analytics = AnalyticsService(session)

    inv.set_stock(product.id, warehouse.id, 5)
    analytics.generate_daily_snapshot(date(2026, 3, 1))

    # Second call for the same date must raise
    with pytest.raises(SnapshotAlreadyExistsError):
        analytics.generate_daily_snapshot(date(2026, 3, 1))


# ---------------------------------------------------------------------------
# Test 4: snapshot via workflow matches direct analytics
# ---------------------------------------------------------------------------


def test_snapshot_via_workflow_matches_direct_analytics(
    session: Session,
) -> None:
    product, warehouse = _seed(session, "SKU-SNAP", "WH-SNAP")

    svc = WorkflowService(session)
    result = svc.execute_snapshot_workflow(
        WorkflowRequest("snap-wf"),
        csv_string=CSV_HEADER + "SKU-SNAP,WH-SNAP,20\n",
        source_name="wf-feed",
        snapshot_date=date(2026, 4, 1),
    )
    assert result.successful is True

    analytics = AnalyticsService(session)
    snapshots = analytics.get_snapshots_by_date(date(2026, 4, 1))

    dashboard = DashboardService(session).get_snapshot_dashboard(date(2026, 4, 1))

    assert dashboard.total_available == sum(s.available_stock for s in snapshots)
    assert len(dashboard.rows) == len(snapshots)


# ---------------------------------------------------------------------------
# Test 5: snapshot export CSV format
# ---------------------------------------------------------------------------


def test_snapshot_export_csv_format(session: Session) -> None:
    product, warehouse = _seed(session, "SKU-SNAP", "WH-SNAP")

    inv = InventoryService(session)
    res_svc = ReservationService(session)
    analytics = AnalyticsService(session)
    export = ExportService(session)

    # stock=8, reservation=3 → available=5
    inv.set_stock(product.id, warehouse.id, 8)
    res_svc.create_reservation(
        product_id=product.id,
        warehouse_id=warehouse.id,
        quantity=3,
        reference="SNAP-FORMAT",
    )

    analytics.generate_daily_snapshot(date(2026, 5, 1))

    csv_text = export.export_daily_snapshot_csv(date(2026, 5, 1))

    reader = csv.reader(io.StringIO(csv_text))
    rows = list(reader)

    # Header check
    assert rows[0] == [
        "snapshot_date",
        "product_id",
        "warehouse_id",
        "physical_stock",
        "reserved_quantity",
        "available_stock",
    ]

    # Data row check — exactly one data row
    assert len(rows) == 2, f"Expected header + 1 data row, got {len(rows)} rows"
    data_row = rows[1]
    assert data_row[0] == "2026-05-01"
    assert data_row[3] == "8"    # physical_stock
    assert data_row[4] == "3"    # reserved_quantity
    assert data_row[5] == "5"    # available_stock
