"""Tests for the application / use-case layer."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from src.application import OrderFulfillmentApp, ReportingApp, StockImportApp
from src.application.order_fulfillment import ReservationRequest
from src.container import Container
from src.exceptions import ConflictError, NotFoundError, ValidationError
from src.models.import_job import ImportJobStatus
from src.models.order import OrderStatus
from src.models.report_job import ReportJobStatus
from src.models.report_request import ReportType
from src.models.reservation import ReservationStatus
from src.services.inventory_service import InventoryService


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

CSV_HEADER = "sku,warehouse_code,quantity\n"


def _seed(session: Session, sku: str = "SKU-1", code: str = "WH-1", qty: int = 20):
    inv = InventoryService(session)
    product = inv.add_product(sku=sku, name="Widget", unit="pcs")
    warehouse = inv.create_warehouse(code=code, name="Main", location="Berlin")
    inv.set_stock(product.id, warehouse.id, qty)
    return product, warehouse


# ---------------------------------------------------------------------------
# StockImportApp
# ---------------------------------------------------------------------------


class TestStockImportApp:
    def test_setup_catalog_creates_product_and_warehouse(
        self, session: Session
    ) -> None:
        c = Container(session)
        app = StockImportApp(c)
        product, warehouse = app.setup_catalog(
            sku="P1", name="Prod", unit="pcs",
            warehouse_code="W1", warehouse_name="WH", warehouse_location="X",
        )
        assert product.sku == "P1"
        assert warehouse.code == "W1"

    def test_import_csv_returns_completed_job(self, session: Session) -> None:
        c = Container(session)
        app = StockImportApp(c)
        app.setup_catalog(
            sku="P1", name="Prod", unit="pcs",
            warehouse_code="W1", warehouse_name="WH", warehouse_location="X",
        )
        job = app.import_csv(CSV_HEADER + "P1,W1,10\n", "test-feed")
        assert job.status is ImportJobStatus.COMPLETED
        assert job.row_count == 1

    def test_preview_csv_returns_rows_without_writing(
        self, session: Session
    ) -> None:
        c = Container(session)
        app = StockImportApp(c)
        rows = app.preview_csv(CSV_HEADER + "SKU-X,WH-X,5\n")
        assert len(rows) == 1
        assert rows[0].sku == "SKU-X"

    def test_import_unknown_sku_job_is_failed(self, session: Session) -> None:
        c = Container(session)
        app = StockImportApp(c)
        job = app.import_csv(CSV_HEADER + "UNKNOWN,WH-1,5\n", "bad-feed")
        assert job.status is ImportJobStatus.FAILED


# ---------------------------------------------------------------------------
# OrderFulfillmentApp
# ---------------------------------------------------------------------------


class TestOrderFulfillmentApp:
    def test_reserve_and_create_order(self, session: Session) -> None:
        product, warehouse = _seed(session)
        c = Container(session)
        app = OrderFulfillmentApp(c)

        requests = [
            ReservationRequest(
                product_id=product.id,
                warehouse_id=warehouse.id,
                quantity=5,
                reference="ORD-001",
            )
        ]
        reservations, order = app.reserve_and_create_order("ORD-001", requests)

        assert len(reservations) == 1
        assert reservations[0].status is ReservationStatus.ACTIVE
        assert order.status is OrderStatus.PENDING
        assert len(order.items) == 1

    def test_confirm_and_complete(self, session: Session) -> None:
        product, warehouse = _seed(session)
        c = Container(session)
        app = OrderFulfillmentApp(c)

        requests = [
            ReservationRequest(
                product_id=product.id,
                warehouse_id=warehouse.id,
                quantity=3,
                reference="ORD-002",
            )
        ]
        _, order = app.reserve_and_create_order("ORD-002", requests)
        completed = app.confirm_and_complete(order.id)

        assert completed.status is OrderStatus.COMPLETED

    def test_cancel_releases_reservation(self, session: Session) -> None:
        product, warehouse = _seed(session)
        c = Container(session)
        app = OrderFulfillmentApp(c)

        requests = [
            ReservationRequest(
                product_id=product.id,
                warehouse_id=warehouse.id,
                quantity=4,
                reference="ORD-003",
            )
        ]
        reservations, order = app.reserve_and_create_order("ORD-003", requests)
        cancelled = app.cancel(order.id)

        assert cancelled.status is OrderStatus.CANCELLED
        session.refresh(reservations[0])
        assert reservations[0].status is ReservationStatus.RELEASED

    def test_duplicate_reference_raises_conflict(self, session: Session) -> None:
        product, warehouse = _seed(session)
        c = Container(session)
        app = OrderFulfillmentApp(c)

        requests = [
            ReservationRequest(
                product_id=product.id,
                warehouse_id=warehouse.id,
                quantity=2,
                reference="DUP",
            )
        ]
        app.reserve_and_create_order("DUP", requests)

        requests2 = [
            ReservationRequest(
                product_id=product.id,
                warehouse_id=warehouse.id,
                quantity=2,
                reference="DUP2",
            )
        ]
        with pytest.raises(ConflictError):
            app.reserve_and_create_order("DUP", requests2)

    def test_overselling_raises_validation_error(self, session: Session) -> None:
        product, warehouse = _seed(session, qty=3)
        c = Container(session)
        app = OrderFulfillmentApp(c)

        with pytest.raises(ValidationError):
            app.reserve_and_create_order(
                "ORD-BIG",
                [
                    ReservationRequest(
                        product_id=product.id,
                        warehouse_id=warehouse.id,
                        quantity=10,
                        reference="ORD-BIG",
                    )
                ],
            )


# ---------------------------------------------------------------------------
# ReportingApp
# ---------------------------------------------------------------------------


class TestReportingApp:
    def test_create_and_run_order_summary_report(
        self, session: Session
    ) -> None:
        c = Container(session)
        app = ReportingApp(c)
        job = app.create_and_run_report(ReportType.ORDER_SUMMARY)
        assert job.status is ReportJobStatus.COMPLETED

    def test_create_and_run_inventory_summary_report(
        self, session: Session
    ) -> None:
        c = Container(session)
        app = ReportingApp(c)
        job = app.create_and_run_report(ReportType.INVENTORY_SUMMARY)
        assert job.status is ReportJobStatus.COMPLETED

    def test_get_inventory_summary_returns_list(
        self, session: Session
    ) -> None:
        _seed(session)
        c = Container(session)
        app = ReportingApp(c)
        rows = app.get_inventory_summary()
        assert isinstance(rows, list)
        assert len(rows) == 1

    def test_export_inventory_csv_contains_header(
        self, session: Session
    ) -> None:
        _seed(session)
        c = Container(session)
        app = ReportingApp(c)
        csv_text = app.export_inventory_csv()
        assert "physical_stock" in csv_text

    def test_export_inventory_csv_empty_when_no_stock(
        self, session: Session
    ) -> None:
        c = Container(session)
        app = ReportingApp(c)
        csv_text = app.export_inventory_csv()
        lines = [l for l in csv_text.splitlines() if l.strip()]
        # Only the header row, no data rows
        assert len(lines) == 1
