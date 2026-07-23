"""Lightweight dependency container for opsboard.

:class:`Container` accepts a single :class:`~sqlalchemy.orm.Session` and
exposes every service as a lazily-constructed property.  Each property
instantiates its service on first access and caches it for the lifetime of
the container instance — matching the per-request / per-unit-of-work scope
already used throughout the codebase.

Usage::

    from src.container import Container

    with session_scope(factory) as session:
        c = Container(session)
        order = c.orders.create_order(reference, lines)

The container does **not** own the session; the caller is responsible for
committing or rolling back.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

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


class Container:
    """Per-session service container.

    All services are constructed lazily and cached for the lifetime of this
    container.  Pass one :class:`~sqlalchemy.orm.Session` per unit of work.

    Parameters
    ----------
    session:
        The active SQLAlchemy session shared by all services in this container.
    """

    __slots__ = (
        "_session",
        "_analytics",
        "_audit",
        "_backoff",
        "_batch_export",
        "_batch_report",
        "_cache",
        "_dashboard",
        "_events",
        "_export",
        "_imports",
        "_inventory",
        "_notifications",
        "_orders",
        "_report_jobs",
        "_reservations",
        "_retry",
        "_scheduler",
        "_template_rendering",
        "_workflows",
    )

    def __init__(self, session: Session) -> None:
        self._session = session
        # All cached service slots start as None.
        self._analytics: AnalyticsService | None = None
        self._audit: AuditService | None = None
        self._backoff: BackoffService | None = None
        self._batch_export: BatchExportService | None = None
        self._batch_report: BatchReportService | None = None
        self._cache: CacheService | None = None
        self._dashboard: DashboardService | None = None
        self._events: EventService | None = None
        self._export: ExportService | None = None
        self._imports: ImportService | None = None
        self._inventory: InventoryService | None = None
        self._notifications: NotificationService | None = None
        self._orders: OrderService | None = None
        self._report_jobs: ReportJobService | None = None
        self._reservations: ReservationService | None = None
        self._retry: RetryService | None = None
        self._scheduler: SchedulerService | None = None
        self._template_rendering: TemplateRenderingService | None = None
        self._workflows: WorkflowService | None = None

    # ------------------------------------------------------------------
    # Service properties — lazily constructed, cached per container
    # ------------------------------------------------------------------

    @property
    def analytics(self) -> AnalyticsService:
        """Return the :class:`AnalyticsService` for this session."""
        if self._analytics is None:
            self._analytics = AnalyticsService(self._session)
        return self._analytics

    @property
    def audit(self) -> AuditService:
        """Return the :class:`AuditService` for this session."""
        if self._audit is None:
            self._audit = AuditService(self._session)
        return self._audit

    @property
    def backoff(self) -> BackoffService:
        """Return the :class:`BackoffService` (stateless, no session needed)."""
        if self._backoff is None:
            self._backoff = BackoffService()
        return self._backoff

    @property
    def batch_export(self) -> BatchExportService:
        """Return the :class:`BatchExportService` for this session."""
        if self._batch_export is None:
            self._batch_export = BatchExportService(self.export)
        return self._batch_export

    @property
    def batch_report(self) -> BatchReportService:
        """Return the :class:`BatchReportService` for this session."""
        if self._batch_report is None:
            self._batch_report = BatchReportService(
                self.dashboard, self.analytics, session=self._session
            )
        return self._batch_report

    @property
    def cache(self) -> CacheService:
        """Return the :class:`CacheService` for this session."""
        if self._cache is None:
            self._cache = CacheService(self._session)
        return self._cache

    @property
    def dashboard(self) -> DashboardService:
        """Return the :class:`DashboardService` for this session."""
        if self._dashboard is None:
            self._dashboard = DashboardService(self._session)
        return self._dashboard

    @property
    def events(self) -> EventService:
        """Return the :class:`EventService` for this session."""
        if self._events is None:
            self._events = EventService(self._session)
        return self._events

    @property
    def export(self) -> ExportService:
        """Return the :class:`ExportService` for this session."""
        if self._export is None:
            self._export = ExportService(self._session)
        return self._export

    @property
    def imports(self) -> ImportService:
        """Return the :class:`ImportService` for this session."""
        if self._imports is None:
            self._imports = ImportService(self._session)
        return self._imports

    @property
    def inventory(self) -> InventoryService:
        """Return the :class:`InventoryService` for this session."""
        if self._inventory is None:
            self._inventory = InventoryService(self._session)
        return self._inventory

    @property
    def notifications(self) -> NotificationService:
        """Return the :class:`NotificationService` for this session."""
        if self._notifications is None:
            self._notifications = NotificationService(self._session)
        return self._notifications

    @property
    def orders(self) -> OrderService:
        """Return the :class:`OrderService` for this session."""
        if self._orders is None:
            self._orders = OrderService(self._session)
        return self._orders

    @property
    def report_jobs(self) -> ReportJobService:
        """Return the :class:`ReportJobService` for this session."""
        if self._report_jobs is None:
            self._report_jobs = ReportJobService(self._session)
        return self._report_jobs

    @property
    def reservations(self) -> ReservationService:
        """Return the :class:`ReservationService` for this session."""
        if self._reservations is None:
            self._reservations = ReservationService(self._session)
        return self._reservations

    @property
    def retry(self) -> RetryService:
        """Return the :class:`RetryService` for this session."""
        if self._retry is None:
            self._retry = RetryService(self._session)
        return self._retry

    @property
    def scheduler(self) -> SchedulerService:
        """Return the :class:`SchedulerService` for this session."""
        if self._scheduler is None:
            self._scheduler = SchedulerService(self._session)
        return self._scheduler

    @property
    def template_rendering(self) -> TemplateRenderingService:
        """Return the :class:`TemplateRenderingService` for this session."""
        if self._template_rendering is None:
            self._template_rendering = TemplateRenderingService(self._session)
        return self._template_rendering

    @property
    def workflows(self) -> WorkflowService:
        """Return the :class:`WorkflowService` for this session."""
        if self._workflows is None:
            self._workflows = WorkflowService(self._session)
        return self._workflows
