"""End-to-end integration tests for Workflow E orchestration.

Workflow E: WorkflowService → AuditService → Analytics → Export → Notification
Real DB sessions. No mocks.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date

import pytest
from sqlalchemy.orm import Session

from src.models import DomainEventType, NotificationStatus, WorkflowStatus
from src.repositories import WorkflowExecutionRepository
from src.schemas import AuditQuery, WorkflowRequest
from src.services import (
    AnalyticsService,
    AuditService,
    EventService,
    ExportService,
    InventoryService,
    NotificationService,
    WorkflowService,
)

# ---------------------------------------------------------------------------
# Helper constants
# ---------------------------------------------------------------------------

CSV_HEADER = "sku,warehouse_code,quantity\n"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _seed(session: Session, sku: str, code: str):
    """Create and return a (product, warehouse) pair."""
    inv = InventoryService(session)
    product = inv.add_product(sku=sku, name=f"Product {sku}", unit="pcs")
    warehouse = inv.create_warehouse(
        code=code, name=f"Warehouse {code}", location="Site A"
    )
    return product, warehouse


# ---------------------------------------------------------------------------
# Test 1: full successful inventory reporting workflow
# ---------------------------------------------------------------------------


def test_inventory_reporting_workflow_full_success(session: Session) -> None:
    _seed(session, "SKU-W1", "WH-W1")

    svc = WorkflowService(session)
    result = svc.execute_inventory_reporting_workflow(
        WorkflowRequest("inv-report", send_notifications=True),
        csv_string=CSV_HEADER + "SKU-W1,WH-W1,15\n",
        source_name="test-feed",
    )

    # Overall success
    assert result.successful is True

    # Step names and order
    assert [s.step_name for s in result.steps] == [
        "import",
        "analytics",
        "export",
        "notifications",
    ]

    # Every step succeeded
    assert all(s.successful for s in result.steps)

    # Domain event recorded
    events = EventService(session).get_events_by_type(DomainEventType.STOCK_IMPORTED)
    assert len(events) == 1

    # Notification was sent
    sent = NotificationService(session).get_notifications_by_status(
        NotificationStatus.SENT
    )
    assert len(sent) == 1

    # Audit trail has "created" and "updated" entries for WorkflowExecution
    entries = AuditService(session).query_audit(
        AuditQuery(entity_type="WorkflowExecution")
    )
    assert len(entries) == 2
    actions = [e.action for e in entries]
    assert actions == ["created", "updated"]


# ---------------------------------------------------------------------------
# Test 2: full successful snapshot workflow
# ---------------------------------------------------------------------------


def test_snapshot_workflow_full_success(session: Session) -> None:
    product, warehouse = _seed(session, "SKU-S1", "WH-S1")

    svc = WorkflowService(session)
    result = svc.execute_snapshot_workflow(
        WorkflowRequest("snapshot"),
        csv_string=CSV_HEADER + "SKU-S1,WH-S1,10\n",
        source_name="daily",
        snapshot_date=date(2026, 3, 1),
    )

    assert result.successful is True
    assert [s.step_name for s in result.steps] == ["import", "analytics", "export"]

    # Snapshot stored with correct figures
    snapshot = AnalyticsService(session).get_snapshot(
        date(2026, 3, 1), product.id, warehouse.id
    )
    assert snapshot.physical_stock == 10
    assert snapshot.available_stock == 10


# ---------------------------------------------------------------------------
# Test 3: workflow failure records audit entry
# ---------------------------------------------------------------------------


def test_workflow_failure_records_audit_entry(session: Session) -> None:
    # No products seeded — CSV will fail at resolve step (unknown SKU)
    svc = WorkflowService(session)
    result = svc.execute_inventory_reporting_workflow(
        WorkflowRequest("inv-report-fail"),
        csv_string=CSV_HEADER + "SKU-MISSING,WH-MISSING,5\n",
        source_name="bad-feed",
    )

    assert result.successful is False
    assert len(result.failed_steps()) == 1

    # Audit: still 2 entries — "created" (RUNNING) and "updated" (FAILED)
    entries = AuditService(session).query_audit(
        AuditQuery(entity_type="WorkflowExecution")
    )
    assert len(entries) == 2
    actions = {e.action for e in entries}
    assert actions == {"created", "updated"}

    # WorkflowExecution in FAILED state with error_message set
    failed = WorkflowExecutionRepository(session).get_by_status(WorkflowStatus.FAILED)
    assert len(failed) == 1
    assert failed[0].error_message is not None
    assert len(failed[0].error_message) > 0


# ---------------------------------------------------------------------------
# Test 4: two workflows produce independent audit trails
# ---------------------------------------------------------------------------


def test_two_workflows_produce_independent_audit_trails(
    session: Session,
) -> None:
    _seed(session, "SKU-W1", "WH-W1")

    svc = WorkflowService(session)

    # Workflow 1 — valid CSV → success
    result1 = svc.execute_inventory_reporting_workflow(
        WorkflowRequest("wf-success"),
        csv_string=CSV_HEADER + "SKU-W1,WH-W1,5\n",
        source_name="feed-1",
    )
    assert result1.successful is True

    # Workflow 2 — malformed header → MalformedCsvError → failure
    result2 = svc.execute_inventory_reporting_workflow(
        WorkflowRequest("wf-failure"),
        csv_string="invalid,cols\nskip,this\n",
        source_name="feed-2",
    )
    assert result2.successful is False

    # 4 total audit entries for WorkflowExecution (2 per workflow)
    entries = AuditService(session).query_audit(
        AuditQuery(entity_type="WorkflowExecution")
    )
    assert len(entries) == 4

    # Group by workflow_execution_id
    by_wf: dict = defaultdict(list)
    for entry in entries:
        by_wf[entry.workflow_execution_id].append(entry)

    # Two distinct workflow execution IDs
    assert len(by_wf) == 2

    # Each group has exactly 2 entries
    for wf_id, group in by_wf.items():
        assert len(group) == 2, f"Expected 2 entries for {wf_id}, got {len(group)}"


# ---------------------------------------------------------------------------
# Test 5: inventory workflow export content
# ---------------------------------------------------------------------------


def test_inventory_workflow_export_content(session: Session) -> None:
    _seed(session, "SKU-W1", "WH-W1")

    svc = WorkflowService(session)
    result = svc.execute_inventory_reporting_workflow(
        WorkflowRequest("inv-export-check"),
        csv_string=CSV_HEADER + "SKU-W1,WH-W1,12\n",
        source_name="export-feed",
    )
    assert result.successful is True

    export = ExportService(session)

    # Inventory summary CSV
    inv_csv = export.export_inventory_summary_csv()
    assert "product_id,warehouse_id,physical_stock,reserved_quantity,available_stock" in inv_csv
    assert "12" in inv_csv

    # Order summary CSV — no orders placed, PENDING count should be 0
    order_csv = export.export_order_summary_csv()
    assert "PENDING,0" in order_csv
