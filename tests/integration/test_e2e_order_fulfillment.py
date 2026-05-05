"""End-to-end tests for Workflow A: CSV Import → Inventory → Reservation →
Order → Analytics → Export.

All tests use real SQLite sessions via the ``session`` fixture in
``tests/conftest.py``. No mocks.
"""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from src.models.domain_event import DomainEventType
from src.models.order import OrderStatus
from src.models.reservation import ReservationStatus
from src.schemas import AuditQuery
from src.services import (
    AnalyticsService,
    EventService,
    ExportService,
    ImportService,
    InventoryService,
    OrderLine,
    OrderService,
    ReservationService,
    InsufficientAvailableStockError,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_csv(sku: str, warehouse_code: str, quantity: int) -> str:
    return f"sku,warehouse_code,quantity\n{sku},{warehouse_code},{quantity}\n"


def _setup_product_and_warehouse(
    session: Session,
    sku: str = "SKU-1",
    warehouse_code: str = "WH-1",
) -> tuple:
    """Create a product and warehouse; return (product, warehouse)."""
    inv = InventoryService(session)
    product = inv.add_product(sku=sku, name=f"Product {sku}", unit="unit")
    warehouse = inv.create_warehouse(
        code=warehouse_code, name=f"Warehouse {warehouse_code}", location="Loc"
    )
    return product, warehouse


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestFullOrderFulfillmentFromImportToExport:
    """Workflow A happy path: import → reserve → order → complete → verify."""

    def test_full_order_fulfillment_from_import_to_export(
        self, session: Session
    ) -> None:
        product, warehouse = _setup_product_and_warehouse(session)

        # 1. Import stock via CSV
        import_svc = ImportService(session)
        csv_data = _build_csv("SKU-1", "WH-1", 20)
        job = import_svc.import_stock_csv(csv_data, "test-source")
        assert job.row_count == 1

        # 2. Reserve 5 units
        reservation_svc = ReservationService(session)
        reservation = reservation_svc.create_reservation(
            product_id=product.id,
            warehouse_id=warehouse.id,
            quantity=5,
            reference="ORD-E2E-001",
        )

        # 3. Create order from the reservation
        order_svc = OrderService(session)
        order = order_svc.create_order(
            reference="ORD-E2E-001",
            lines=[OrderLine(reservation_id=reservation.id, quantity=5)],
        )

        # 4. Confirm the order
        order = order_svc.confirm_order(order.id)
        assert order.status == OrderStatus.CONFIRMED

        # 5. Complete the order
        order = order_svc.complete_order(order.id)
        assert order.status == OrderStatus.COMPLETED

        # 6. Physical stock unchanged at 20
        inv = InventoryService(session)
        assert inv.get_stock(product.id, warehouse.id) == 20

        # 7. Reserved quantity is 0 (reservation fulfilled, no longer active)
        assert reservation_svc.get_reserved_quantity(product.id, warehouse.id) == 0

        # 8. Analytics shows COMPLETED = 1
        analytics = AnalyticsService(session)
        order_summary = analytics.get_order_summary()
        assert order_summary[OrderStatus.COMPLETED] == 1

        # 9. Export CSV contains the product/warehouse row
        export_svc = ExportService(session)
        inv_csv = export_svc.export_inventory_summary_csv()
        assert str(product.id) in inv_csv
        assert str(warehouse.id) in inv_csv

        # 10. Export order CSV shows COMPLETED,1
        order_csv = export_svc.export_order_summary_csv()
        assert "COMPLETED,1" in order_csv

        # 11. STOCK_IMPORTED event recorded
        event_svc = EventService(session)
        imported_events = event_svc.get_events_by_type(DomainEventType.STOCK_IMPORTED)
        assert len(imported_events) == 1

        # 12. ORDER_COMPLETED event recorded
        completed_events = event_svc.get_events_by_type(
            DomainEventType.ORDER_COMPLETED
        )
        assert len(completed_events) == 1


class TestOrderCancellationRestoresAvailability:
    """Cancelling an order releases the reservation and restores availability."""

    def test_order_cancellation_restores_availability(
        self, session: Session
    ) -> None:
        product, warehouse = _setup_product_and_warehouse(session)

        # Import 10 units
        import_svc = ImportService(session)
        job = import_svc.import_stock_csv(
            _build_csv("SKU-1", "WH-1", 10), "cancel-test"
        )
        assert job.row_count == 1

        # Reserve 7 units
        reservation_svc = ReservationService(session)
        reservation = reservation_svc.create_reservation(
            product_id=product.id,
            warehouse_id=warehouse.id,
            quantity=7,
            reference="CANCEL-001",
        )

        # Create order
        order_svc = OrderService(session)
        order = order_svc.create_order(
            reference="CANCEL-001",
            lines=[OrderLine(reservation_id=reservation.id, quantity=7)],
        )

        # Available stock before cancel: 10 - 7 = 3
        assert reservation_svc.get_available_stock(product.id, warehouse.id) == 3

        # Cancel the order
        order = order_svc.cancel_order(order.id)
        assert order.status == OrderStatus.CANCELLED

        # Reservation is now RELEASED
        session.refresh(reservation)
        assert reservation.status == ReservationStatus.RELEASED

        # Available stock restored to 10
        assert reservation_svc.get_available_stock(product.id, warehouse.id) == 10

        # Analytics shows CANCELLED = 1
        analytics = AnalyticsService(session)
        order_summary = analytics.get_order_summary()
        assert order_summary[OrderStatus.CANCELLED] == 1

        # ORDER_CANCELLED event recorded
        event_svc = EventService(session)
        cancelled_events = event_svc.get_events_by_type(
            DomainEventType.ORDER_CANCELLED
        )
        assert len(cancelled_events) == 1

        # Export CSV contains 0 active reservations
        export_svc = ExportService(session)
        res_csv = export_svc.export_reservation_summary_csv()
        # The ACTIVE row should show 0
        lines = res_csv.strip().splitlines()
        active_line = next((l for l in lines if l.startswith("ACTIVE")), None)
        assert active_line is not None
        assert active_line.endswith(",0")


class TestOrderLifecycleCompleteStateTransitions:
    """Full PENDING → CONFIRMED → COMPLETED state-machine walkthrough."""

    def test_order_lifecycle_complete_state_transitions(
        self, session: Session
    ) -> None:
        # Create product, warehouse, and stock directly
        inv = InventoryService(session)
        product = inv.add_product(sku="SKU-LIFE", name="Lifecycle Product", unit="ea")
        warehouse = inv.create_warehouse(
            code="WH-LIFE", name="Lifecycle WH", location="Z"
        )
        inv.set_stock(product.id, warehouse.id, 15)

        # Reserve 5 units
        reservation_svc = ReservationService(session)
        reservation = reservation_svc.create_reservation(
            product_id=product.id,
            warehouse_id=warehouse.id,
            quantity=5,
            reference="LIFE-001",
        )
        assert reservation.status == ReservationStatus.ACTIVE

        # Create order → PENDING
        order_svc = OrderService(session)
        order = order_svc.create_order(
            reference="LIFE-001",
            lines=[OrderLine(reservation_id=reservation.id, quantity=5)],
        )
        assert order.status == OrderStatus.PENDING

        # Confirm → CONFIRMED
        order = order_svc.confirm_order(order.id)
        assert order.status == OrderStatus.CONFIRMED

        # Complete → COMPLETED
        order = order_svc.complete_order(order.id)
        assert order.status == OrderStatus.COMPLETED

        # Reservation is now FULFILLED
        session.refresh(reservation)
        assert reservation.status == ReservationStatus.FULFILLED

        # Physical stock still 15
        assert inv.get_stock(product.id, warehouse.id) == 15

        # Analytics: available_stock = 15 (fulfilled res no longer reduces)
        analytics = AnalyticsService(session)
        summary_rows = analytics.get_inventory_summary()
        row = next(
            r
            for r in summary_rows
            if r.product_id == product.id and r.warehouse_id == warehouse.id
        )
        assert row.available_stock == 15


class TestMultiProductMultiWarehouseOrder:
    """One order spanning two products at two different warehouses."""

    def test_multi_product_multi_warehouse_order(
        self, session: Session
    ) -> None:
        inv = InventoryService(session)

        # Create 2 products
        p1 = inv.add_product(sku="P1", name="Product 1", unit="ea")
        p2 = inv.add_product(sku="P2", name="Product 2", unit="ea")

        # Create 2 warehouses
        wh_a = inv.create_warehouse(code="WH-A", name="Warehouse A", location="A")
        wh_b = inv.create_warehouse(code="WH-B", name="Warehouse B", location="B")

        # Import stock: P1@WH-A=10, P2@WH-B=8
        import_svc = ImportService(session)
        import_svc.import_stock_csv(
            "sku,warehouse_code,quantity\nP1,WH-A,10\nP2,WH-B,8\n",
            "multi-import",
        )

        # Reserve P1@WH-A=3 and P2@WH-B=4 under same reference
        res_svc = ReservationService(session)
        res1 = res_svc.create_reservation(
            product_id=p1.id,
            warehouse_id=wh_a.id,
            quantity=3,
            reference="MULTI-001",
        )
        res2 = res_svc.create_reservation(
            product_id=p2.id,
            warehouse_id=wh_b.id,
            quantity=4,
            reference="MULTI-001",
        )

        # One order with both lines
        order_svc = OrderService(session)
        order = order_svc.create_order(
            reference="MULTI-001",
            lines=[
                OrderLine(reservation_id=res1.id, quantity=3),
                OrderLine(reservation_id=res2.id, quantity=4),
            ],
        )

        # Confirm then complete
        order = order_svc.confirm_order(order.id)
        order = order_svc.complete_order(order.id)
        assert order.status == OrderStatus.COMPLETED

        # Both reservations are FULFILLED
        session.refresh(res1)
        session.refresh(res2)
        assert res1.status == ReservationStatus.FULFILLED
        assert res2.status == ReservationStatus.FULFILLED

        # Analytics summary has 2 rows (one per stock record)
        analytics = AnalyticsService(session)
        summary = analytics.get_inventory_summary()
        assert len(summary) == 2

        # P1@WH-A: physical=10, available=10 (reservation fulfilled)
        row_p1 = next(
            r for r in summary if r.product_id == p1.id and r.warehouse_id == wh_a.id
        )
        assert row_p1.physical_stock == 10
        assert row_p1.available_stock == 10

        # P2@WH-B: physical=8, available=8
        row_p2 = next(
            r for r in summary if r.product_id == p2.id and r.warehouse_id == wh_b.id
        )
        assert row_p2.physical_stock == 8
        assert row_p2.available_stock == 8


class TestReservationPreventsOverselling:
    """Reservations guard against overselling; fulfillment restores capacity."""

    def test_reservation_prevents_overselling(
        self, session: Session
    ) -> None:
        # Import 5 units
        inv = InventoryService(session)
        product = inv.add_product(sku="SKU-OS", name="Oversell Product", unit="ea")
        warehouse = inv.create_warehouse(
            code="WH-OS", name="Oversell WH", location="X"
        )
        import_svc = ImportService(session)
        import_svc.import_stock_csv(
            _build_csv("SKU-OS", "WH-OS", 5), "oversell-import"
        )

        # Reserve all 5 units
        res_svc = ReservationService(session)
        reservation = res_svc.create_reservation(
            product_id=product.id,
            warehouse_id=warehouse.id,
            quantity=5,
            reference="OVERSELL-001",
        )

        # Available stock == 0
        assert res_svc.get_available_stock(product.id, warehouse.id) == 0

        # Second reservation for 1 unit must raise
        with pytest.raises(InsufficientAvailableStockError):
            res_svc.create_reservation(
                product_id=product.id,
                warehouse_id=warehouse.id,
                quantity=1,
                reference="OVERSELL-FAIL",
            )

        # Complete the first reservation via a full order flow
        order_svc = OrderService(session)
        order = order_svc.create_order(
            reference="OVERSELL-001",
            lines=[OrderLine(reservation_id=reservation.id, quantity=5)],
        )
        order_svc.confirm_order(order.id)
        order_svc.complete_order(order.id)

        # Available stock restored to 5 (fulfilled res no longer counted)
        assert res_svc.get_available_stock(product.id, warehouse.id) == 5

        # New reservation for 5 units now succeeds
        new_res = res_svc.create_reservation(
            product_id=product.id,
            warehouse_id=warehouse.id,
            quantity=5,
            reference="OVERSELL-REFILL",
        )
        assert new_res.status == ReservationStatus.ACTIVE
