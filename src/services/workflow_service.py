"""Workflow service: synchronous orchestration of operational steps."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date

from sqlalchemy.orm import Session

from src.models.base import utcnow
from src.models.import_job import ImportJobStatus
from src.models.workflow_execution import WorkflowExecution, WorkflowStatus
from src.repositories import WorkflowExecutionRepository
from src.schemas import WorkflowRequest, WorkflowResult
from src.services.analytics_service import AnalyticsService
from src.services.audit_service import AuditService
from src.services.export_service import ExportService
from src.services.import_service import ImportService
from src.services.notification_service import NotificationService
from src.value_objects import WorkflowStep


class WorkflowError(Exception):
    """Base class for workflow-related errors."""


class _StepFailed(Exception):
    """Internal signal that a workflow step did not succeed."""

    def __init__(self, step: WorkflowStep) -> None:
        super().__init__(step.message)
        self.step = step


class WorkflowService:
    """Runs multi-step operational workflows synchronously and audits them.

    Each workflow creates a :class:`WorkflowExecution`, runs an ordered set of
    steps that delegate entirely to the existing import, analytics, export, and
    notification services, and records audit entries for the run. The first
    failing step aborts the workflow and marks the execution ``FAILED``; earlier
    steps are not rolled back.
    """

    def __init__(self, session: Session) -> None:
        self._session = session
        self._import = ImportService(session)
        self._analytics = AnalyticsService(session)
        self._export = ExportService(session)
        self._notifications = NotificationService(session)
        self._audit = AuditService(session)
        self._workflows = WorkflowExecutionRepository(session)

    def execute_inventory_reporting_workflow(
        self,
        request: WorkflowRequest,
        *,
        csv_string: str,
        source_name: str,
    ) -> WorkflowResult:
        """Import stock, summarize inventory, export CSV, optionally notify."""

        def build(steps: list[WorkflowStep]) -> None:
            steps.append(
                self._step(
                    "import",
                    lambda: self._do_import(csv_string, source_name),
                )
            )
            steps.append(
                self._step("analytics", self._do_inventory_analytics)
            )
            steps.append(self._step("export", self._do_inventory_export))
            if request.send_notifications:
                steps.append(
                    self._step(
                        "notifications",
                        lambda: self._do_notify(
                            "Inventory report ready",
                            "Inventory summary export complete.",
                        ),
                    )
                )

        return self._run(request, build)

    def execute_snapshot_workflow(
        self,
        request: WorkflowRequest,
        *,
        csv_string: str,
        source_name: str,
        snapshot_date: date,
    ) -> WorkflowResult:
        """Import stock, snapshot the day, export CSV, optionally notify."""

        def build(steps: list[WorkflowStep]) -> None:
            steps.append(
                self._step(
                    "import",
                    lambda: self._do_import(csv_string, source_name),
                )
            )
            steps.append(
                self._step(
                    "analytics",
                    lambda: self._do_snapshot_analytics(snapshot_date),
                )
            )
            steps.append(
                self._step(
                    "export",
                    lambda: self._do_snapshot_export(snapshot_date),
                )
            )
            if request.send_notifications:
                steps.append(
                    self._step(
                        "notifications",
                        lambda: self._do_notify(
                            "Daily snapshot ready",
                            f"Snapshot for {snapshot_date} complete.",
                        ),
                    )
                )

        return self._run(request, build)

    def _run(
        self,
        request: WorkflowRequest,
        build: Callable[[list[WorkflowStep]], None],
    ) -> WorkflowResult:
        execution = self._workflows.add(
            WorkflowExecution(
                workflow_name=request.workflow_name,
                status=WorkflowStatus.RUNNING,
            )
        )
        self._audit.record_creation(
            "WorkflowExecution",
            str(execution.id),
            {
                "workflow_name": request.workflow_name,
                "status": WorkflowStatus.RUNNING.value,
            },
            workflow_execution_id=execution.id,
        )

        steps: list[WorkflowStep] = []
        try:
            build(steps)
        except _StepFailed as failed:
            steps.append(failed.step)
            self._finalize(execution, WorkflowStatus.FAILED, failed.step.message)
            return WorkflowResult(successful=False, steps=steps)

        self._finalize(execution, WorkflowStatus.COMPLETED, None)
        return WorkflowResult(successful=True, steps=steps)

    def _finalize(
        self,
        execution: WorkflowExecution,
        status: WorkflowStatus,
        error_message: str | None,
    ) -> None:
        old_state = {"status": execution.status.value}
        execution.status = status
        execution.completed_at = utcnow()
        execution.error_message = error_message
        self._session.flush()
        self._audit.record_change(
            "WorkflowExecution",
            str(execution.id),
            old_state,
            {"status": status.value, "error_message": error_message},
            workflow_execution_id=execution.id,
        )

    @staticmethod
    def _step(name: str, action: Callable[[], str]) -> WorkflowStep:
        """Run one step, returning a successful record or raising on failure."""
        try:
            message = action()
        except Exception as exc:  # noqa: BLE001 - recorded as a failed step
            raise _StepFailed(WorkflowStep(name, False, str(exc))) from exc
        return WorkflowStep(name, True, message)

    def _do_import(self, csv_string: str, source_name: str) -> str:
        job = self._import.import_stock_csv(csv_string, source_name)
        if job.status is ImportJobStatus.FAILED:
            raise WorkflowError(job.error_message or "import failed")
        return f"imported {job.row_count} rows"

    def _do_inventory_analytics(self) -> str:
        rows = self._analytics.get_inventory_summary()
        return f"{len(rows)} summary rows"

    def _do_inventory_export(self) -> str:
        csv_text = self._export.export_inventory_summary_csv()
        return f"{len(csv_text)} bytes exported"

    def _do_snapshot_analytics(self, snapshot_date: date) -> str:
        created = self._analytics.generate_daily_snapshot(snapshot_date)
        return f"{len(created)} snapshot rows"

    def _do_snapshot_export(self, snapshot_date: date) -> str:
        csv_text = self._export.export_daily_snapshot_csv(snapshot_date)
        return f"{len(csv_text)} bytes exported"

    def _do_notify(self, subject: str, body: str) -> str:
        notification = self._notifications.create_notification(subject, body)
        self._notifications.mark_sent(notification.id)
        return f"notification {notification.id} sent"
