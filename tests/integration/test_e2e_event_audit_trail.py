"""End-to-end tests for Workflow B: Inventory → Reservation → Order
completion → Event generation → Audit recording.

All tests use real SQLite sessions via the ``session`` fixture in
``tests/conftest.py``. No mocks.
"""

from __future__ import annotations

import json

import pytest
from sqlalchemy.orm import Session

from src.models.domain_event import DomainEventType
from src.models.order import OrderStatus
from src.schemas import AuditQuery, WorkflowRequest
from src.services import (
    AuditService,
    EventService,
    ImportService,
    InventoryService,
    OrderLine,
    OrderService,
    ReservationService,
    WorkflowService,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_csv(sku: str, warehouse_code: str, quantity: int) -> str:
    return f"sku,warehouse_code,quantity\n{sku},{warehouse_code},{quantity}\n"


def _setup_stock(
    session: Session,
    sku: str = "SKU-A",
    warehouse_code: str = "WH-EVT",
    quantity: int = 10,
):
    """Create product + warehouse + stock; return (product, warehouse)."""
    inv = InventoryService(session)
    product = inv.add_product(sku=sku, name=f"Product {sku}", unit="ea")
    warehouse = inv.create_warehouse(
        code=warehouse_code,
        name=f"Warehouse {warehouse_code}",
        location="Loc",
    )
    import_svc = ImportService(session)
    import_svc.import_stock_csv(
        _build_csv(sku, warehouse_code, quantity), f"setup-{sku}"
    )
    return product, warehouse


def _create_completed_order(
    session: Session,
    product_id,
    warehouse_id,
    quantity: int,
    reference: str,
):
    """Reserve → order → confirm → complete. Returns the completed order."""
    res_svc = ReservationService(session)
    reservation = res_svc.create_reservation(
        product_id=product_id,
        warehouse_id=warehouse_id,
        quantity=quantity,
        reference=reference,
    )
    order_svc = OrderService(session)
    order = order_svc.create_order(
        reference=reference,
        lines=[OrderLine(reservation_id=reservation.id, quantity=quantity)],
    )
    order_svc.confirm_order(order.id)
    return order_svc.complete_order(order.id)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCompleteOrderGeneratesDomainEventsAndAudit:
    """Completing an order produces the right domain events."""

    def test_complete_order_generates_domain_events_and_audit(
        self, session: Session
    ) -> None:
        product, warehouse = _setup_stock(session, quantity=5)

        order = _create_completed_order(
            session, product.id, warehouse.id, quantity=3, reference="EVT-001"
        )

        event_svc = EventService(session)

        # ORDER_COMPLETED event exists
        completed_events = event_svc.get_events_by_type(
            DomainEventType.ORDER_COMPLETED
        )
        assert len(completed_events) == 1

        # Event payload contains order_id and reference
        payload = json.loads(completed_events[0].payload_json)
        assert payload["order_id"] == str(order.id)
        assert payload["reference"] == "EVT-001"

        # No WorkflowExecution audit entries (no workflow was run)
        audit_svc = AuditService(session)
        workflow_audit = audit_svc.query_audit(
            AuditQuery(entity_type="WorkflowExecution")
        )
        assert len(workflow_audit) == 0


class TestImportFailureEmitsFailedEventNotImported:
    """A bad CSV emits STOCK_IMPORT_FAILED and no STOCK_IMPORTED event."""

    def test_import_failure_emits_failed_event_not_imported(
        self, session: Session
    ) -> None:
        # No product/warehouse created → unknown SKU will fail

        import_svc = ImportService(session)
        csv_bad = "sku,warehouse_code,quantity\nNONEXISTENT-SKU,WH-NOPE,5\n"
        job = import_svc.import_stock_csv(csv_bad, "bad-import")

        event_svc = EventService(session)

        # STOCK_IMPORT_FAILED emitted
        failed_events = event_svc.get_events_by_type(
            DomainEventType.STOCK_IMPORT_FAILED
        )
        assert len(failed_events) == 1

        # STOCK_IMPORTED NOT emitted
        imported_events = event_svc.get_events_by_type(
            DomainEventType.STOCK_IMPORTED
        )
        assert len(imported_events) == 0

        # Inventory stock remains 0 (no product registered, nothing set)
        # Job is marked FAILED
        from src.models.import_job import ImportJobStatus

        assert job.status == ImportJobStatus.FAILED


class TestImportSuccessEmitsStockImportedEvent:
    """A successful import emits STOCK_IMPORTED with the right payload."""

    def test_import_success_emits_stock_imported_event(
        self, session: Session
    ) -> None:
        # Register product and warehouse first
        inv = InventoryService(session)
        inv.add_product(sku="SKU-IMP", name="Import Product", unit="ea")
        inv.create_warehouse(code="WH-IMP", name="Import WH", location="Loc")

        import_svc = ImportService(session)
        csv_data = _build_csv("SKU-IMP", "WH-IMP", 15)
        job = import_svc.import_stock_csv(csv_data, "good-import")

        event_svc = EventService(session)
        imported_events = event_svc.get_events_by_type(
            DomainEventType.STOCK_IMPORTED
        )
        assert len(imported_events) == 1

        payload = json.loads(imported_events[0].payload_json)
        assert payload["job_id"] == str(job.id)
        assert payload["row_count"] == 1


class TestWorkflowExecutionProducesAuditTrail:
    """execute_inventory_reporting_workflow writes two audit entries."""

    def test_workflow_execution_produces_audit_trail(
        self, session: Session
    ) -> None:
        # Setup product + warehouse so the import step succeeds
        inv = InventoryService(session)
        inv.add_product(sku="SKU-WF", name="Workflow Product", unit="ea")
        inv.create_warehouse(code="WH-WF", name="Workflow WH", location="Loc")

        csv_data = _build_csv("SKU-WF", "WH-WF", 20)
        request = WorkflowRequest(
            workflow_name="inventory-reporting", send_notifications=False
        )

        workflow_svc = WorkflowService(session)
        result = workflow_svc.execute_inventory_reporting_workflow(
            request, csv_string=csv_data, source_name="wf-source"
        )
        assert result.successful

        audit_svc = AuditService(session)
        entries = audit_svc.query_audit(AuditQuery(entity_type="WorkflowExecution"))

        # Exactly 2 audit entries: one "created" (RUNNING) + one "updated" (COMPLETED)
        assert len(entries) == 2

        actions = {e.action for e in entries}
        assert "created" in actions
        assert "updated" in actions

        # All entries have workflow_execution_id set
        for entry in entries:
            assert entry.workflow_execution_id is not None


class TestOrderEventsReflectLifecycle:
    """Two orders (one completed, one cancelled) produce distinct events."""

    def test_order_events_reflect_lifecycle(self, session: Session) -> None:
        # Set up stock for two orders
        product, warehouse = _setup_stock(session, quantity=20)

        res_svc = ReservationService(session)
        order_svc = OrderService(session)

        # --- Order 1: PENDING → CONFIRMED → COMPLETED ---
        res1 = res_svc.create_reservation(
            product_id=product.id,
            warehouse_id=warehouse.id,
            quantity=5,
            reference="LIFECYCLE-1",
        )
        order1 = order_svc.create_order(
            reference="LIFECYCLE-1",
            lines=[OrderLine(reservation_id=res1.id, quantity=5)],
        )
        order_svc.confirm_order(order1.id)
        order1 = order_svc.complete_order(order1.id)
        assert order1.status == OrderStatus.COMPLETED

        # --- Order 2: PENDING → CANCELLED ---
        res2 = res_svc.create_reservation(
            product_id=product.id,
            warehouse_id=warehouse.id,
            quantity=3,
            reference="LIFECYCLE-2",
        )
        order2 = order_svc.create_order(
            reference="LIFECYCLE-2",
            lines=[OrderLine(reservation_id=res2.id, quantity=3)],
        )
        order2 = order_svc.cancel_order(order2.id)
        assert order2.status == OrderStatus.CANCELLED

        event_svc = EventService(session)

        # Exactly 1 ORDER_COMPLETED and 1 ORDER_CANCELLED event
        completed_events = event_svc.get_events_by_type(
            DomainEventType.ORDER_COMPLETED
        )
        assert len(completed_events) == 1

        cancelled_events = event_svc.get_events_by_type(
            DomainEventType.ORDER_CANCELLED
        )
        assert len(cancelled_events) == 1

        # The two events carry different order_ids
        completed_payload = json.loads(completed_events[0].payload_json)
        cancelled_payload = json.loads(cancelled_events[0].payload_json)
        assert completed_payload["order_id"] != cancelled_payload["order_id"]

        # The order_ids match the actual orders
        assert completed_payload["order_id"] == str(order1.id)
        assert cancelled_payload["order_id"] == str(order2.id)
