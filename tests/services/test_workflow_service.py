"""Tests for :class:`WorkflowService`."""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy.orm import Session

from src.models import NotificationStatus, WorkflowStatus
from src.repositories import WorkflowExecutionRepository
from src.schemas import AuditQuery, WorkflowRequest
from src.services import (
    AuditService,
    InventoryService,
    NotificationService,
    WorkflowService,
)

CSV_HEADER = "sku,warehouse_code,quantity\n"


@pytest.fixture
def inventory(session: Session) -> InventoryService:
    return InventoryService(session)


@pytest.fixture
def workflows(session: Session) -> WorkflowService:
    return WorkflowService(session)


def _seed_catalog(inventory: InventoryService) -> None:
    inventory.add_product(sku="SKU-1", name="Widget", unit="pcs")
    inventory.create_warehouse(code="WH-1", name="Main", location="B")


def _valid_csv() -> str:
    return CSV_HEADER + "SKU-1,WH-1,10\n"


class TestInventoryReportingWorkflow:
    def test_success_runs_all_steps(
        self,
        session: Session,
        inventory: InventoryService,
        workflows: WorkflowService,
    ) -> None:
        _seed_catalog(inventory)
        result = workflows.execute_inventory_reporting_workflow(
            WorkflowRequest("inventory_reporting"),
            csv_string=_valid_csv(),
            source_name="feed",
        )

        assert result.successful
        assert [s.step_name for s in result.steps] == [
            "import",
            "analytics",
            "export",
        ]
        assert all(s.successful for s in result.steps)

        executions = WorkflowExecutionRepository(session).get_by_status(
            WorkflowStatus.COMPLETED
        )
        assert len(executions) == 1
        assert executions[0].completed_at is not None

    def test_notifications_step_optional(
        self,
        session: Session,
        inventory: InventoryService,
        workflows: WorkflowService,
    ) -> None:
        _seed_catalog(inventory)
        result = workflows.execute_inventory_reporting_workflow(
            WorkflowRequest("inventory_reporting", send_notifications=True),
            csv_string=_valid_csv(),
            source_name="feed",
        )

        assert result.successful
        assert [s.step_name for s in result.steps][-1] == "notifications"
        sent = NotificationService(session).get_notifications_by_status(
            NotificationStatus.SENT
        )
        assert len(sent) == 1

    def test_no_notifications_by_default(
        self,
        session: Session,
        inventory: InventoryService,
        workflows: WorkflowService,
    ) -> None:
        _seed_catalog(inventory)
        workflows.execute_inventory_reporting_workflow(
            WorkflowRequest("inventory_reporting"),
            csv_string=_valid_csv(),
            source_name="feed",
        )
        sent = NotificationService(session).get_notifications_by_status(
            NotificationStatus.SENT
        )
        assert sent == []

    def test_import_failure_marks_workflow_failed(
        self,
        session: Session,
        inventory: InventoryService,
        workflows: WorkflowService,
    ) -> None:
        # No catalog seeded: the unknown SKU makes the import job FAIL.
        result = workflows.execute_inventory_reporting_workflow(
            WorkflowRequest("inventory_reporting"),
            csv_string=_valid_csv(),
            source_name="feed",
        )

        assert not result.successful
        assert result.steps[-1].step_name == "import"
        assert not result.steps[-1].successful
        assert result.failed_steps()

        failed = WorkflowExecutionRepository(session).get_by_status(
            WorkflowStatus.FAILED
        )
        assert len(failed) == 1
        assert failed[0].error_message

    def test_malformed_csv_marks_workflow_failed(
        self,
        session: Session,
        inventory: InventoryService,
        workflows: WorkflowService,
    ) -> None:
        _seed_catalog(inventory)
        result = workflows.execute_inventory_reporting_workflow(
            WorkflowRequest("inventory_reporting"),
            csv_string="not,a,valid\nheader,row,here\n",
            source_name="feed",
        )
        assert not result.successful
        assert result.steps[-1].step_name == "import"


class TestSnapshotWorkflow:
    def test_success_runs_all_steps(
        self,
        session: Session,
        inventory: InventoryService,
        workflows: WorkflowService,
    ) -> None:
        _seed_catalog(inventory)
        result = workflows.execute_snapshot_workflow(
            WorkflowRequest("snapshot"),
            csv_string=_valid_csv(),
            source_name="feed",
            snapshot_date=date(2026, 1, 1),
        )

        assert result.successful
        assert [s.step_name for s in result.steps] == [
            "import",
            "analytics",
            "export",
        ]

    def test_duplicate_snapshot_marks_workflow_failed(
        self,
        session: Session,
        inventory: InventoryService,
        workflows: WorkflowService,
    ) -> None:
        _seed_catalog(inventory)
        snapshot_date = date(2026, 1, 1)
        workflows.execute_snapshot_workflow(
            WorkflowRequest("snapshot"),
            csv_string=_valid_csv(),
            source_name="feed",
            snapshot_date=snapshot_date,
        )
        # Second run for the same date fails at the analytics step.
        result = workflows.execute_snapshot_workflow(
            WorkflowRequest("snapshot"),
            csv_string=_valid_csv(),
            source_name="feed",
            snapshot_date=snapshot_date,
        )
        assert not result.successful
        assert result.steps[-1].step_name == "analytics"
        assert not result.steps[-1].successful

    def test_notifications_step_optional(
        self,
        session: Session,
        inventory: InventoryService,
        workflows: WorkflowService,
    ) -> None:
        _seed_catalog(inventory)
        result = workflows.execute_snapshot_workflow(
            WorkflowRequest("snapshot", send_notifications=True),
            csv_string=_valid_csv(),
            source_name="feed",
            snapshot_date=date(2026, 1, 1),
        )
        assert result.successful
        assert [s.step_name for s in result.steps][-1] == "notifications"
        sent = NotificationService(session).get_notifications_by_status(
            NotificationStatus.SENT
        )
        assert len(sent) == 1


class TestWorkflowAuditTrail:
    def test_workflow_records_audit_entries(
        self,
        session: Session,
        inventory: InventoryService,
        workflows: WorkflowService,
    ) -> None:
        _seed_catalog(inventory)
        workflows.execute_inventory_reporting_workflow(
            WorkflowRequest("inventory_reporting"),
            csv_string=_valid_csv(),
            source_name="feed",
        )
        entries = AuditService(session).query_audit(
            AuditQuery(entity_type="WorkflowExecution")
        )
        # One creation (RUNNING) and one change (COMPLETED).
        actions = sorted(e.action for e in entries)
        assert actions == ["created", "updated"]
        assert all(e.workflow_execution_id is not None for e in entries)

    def test_failed_workflow_records_audit_entries(
        self,
        session: Session,
        inventory: InventoryService,
        workflows: WorkflowService,
    ) -> None:
        result = workflows.execute_inventory_reporting_workflow(
            WorkflowRequest("inventory_reporting"),
            csv_string=_valid_csv(),
            source_name="feed",
        )
        assert not result.successful
        entries = AuditService(session).query_audit(
            AuditQuery(entity_type="WorkflowExecution")
        )
        assert sorted(e.action for e in entries) == ["created", "updated"]
