"""Tests for the lightweight dependency container."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from src.container import Container
from src.services.analytics_service import AnalyticsService
from src.services.audit_service import AuditService
from src.services.backoff_service import BackoffService
from src.services.batch_export_service import BatchExportService
from src.services.batch_report_service import BatchReportService
from src.services.cache_service import CacheService
from src.services.dashboard_service import DashboardService
from src.services.event_service import EventService
from src.services.export_service import ExportService
from src.services.import_service import ImportService
from src.services.inventory_service import InventoryService
from src.services.notification_service import NotificationService
from src.services.order_service import OrderService
from src.services.report_job_service import ReportJobService
from src.services.reservation_service import ReservationService
from src.services.retry_service import RetryService
from src.services.scheduler_service import SchedulerService
from src.services.template_rendering_service import TemplateRenderingService
from src.services.workflow_service import WorkflowService


@pytest.fixture
def container(session: Session) -> Container:
    return Container(session)


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_container_created_with_session(session: Session) -> None:
    c = Container(session)
    assert c is not None


# ---------------------------------------------------------------------------
# Each property returns the right service type
# ---------------------------------------------------------------------------


def test_analytics_property(container: Container) -> None:
    assert isinstance(container.analytics, AnalyticsService)


def test_audit_property(container: Container) -> None:
    assert isinstance(container.audit, AuditService)


def test_backoff_property(container: Container) -> None:
    assert isinstance(container.backoff, BackoffService)


def test_batch_export_property(container: Container) -> None:
    assert isinstance(container.batch_export, BatchExportService)


def test_batch_report_property(container: Container) -> None:
    assert isinstance(container.batch_report, BatchReportService)


def test_cache_property(container: Container) -> None:
    assert isinstance(container.cache, CacheService)


def test_dashboard_property(container: Container) -> None:
    assert isinstance(container.dashboard, DashboardService)


def test_events_property(container: Container) -> None:
    assert isinstance(container.events, EventService)


def test_export_property(container: Container) -> None:
    assert isinstance(container.export, ExportService)


def test_imports_property(container: Container) -> None:
    assert isinstance(container.imports, ImportService)


def test_inventory_property(container: Container) -> None:
    assert isinstance(container.inventory, InventoryService)


def test_notifications_property(container: Container) -> None:
    assert isinstance(container.notifications, NotificationService)


def test_orders_property(container: Container) -> None:
    assert isinstance(container.orders, OrderService)


def test_report_jobs_property(container: Container) -> None:
    assert isinstance(container.report_jobs, ReportJobService)


def test_reservations_property(container: Container) -> None:
    assert isinstance(container.reservations, ReservationService)


def test_retry_property(container: Container) -> None:
    assert isinstance(container.retry, RetryService)


def test_scheduler_property(container: Container) -> None:
    assert isinstance(container.scheduler, SchedulerService)


def test_template_rendering_property(container: Container) -> None:
    assert isinstance(container.template_rendering, TemplateRenderingService)


def test_workflows_property(container: Container) -> None:
    assert isinstance(container.workflows, WorkflowService)


# ---------------------------------------------------------------------------
# Lazy caching — same instance returned on repeated access
# ---------------------------------------------------------------------------


def test_inventory_is_cached(container: Container) -> None:
    assert container.inventory is container.inventory


def test_orders_is_cached(container: Container) -> None:
    assert container.orders is container.orders


def test_reservations_is_cached(container: Container) -> None:
    assert container.reservations is container.reservations


def test_analytics_is_cached(container: Container) -> None:
    assert container.analytics is container.analytics


def test_backoff_is_cached(container: Container) -> None:
    assert container.backoff is container.backoff


# ---------------------------------------------------------------------------
# Independent containers use independent service instances
# ---------------------------------------------------------------------------


def test_two_containers_produce_independent_services(session: Session) -> None:
    c1 = Container(session)
    c2 = Container(session)
    assert c1.inventory is not c2.inventory
    assert c1.orders is not c2.orders
