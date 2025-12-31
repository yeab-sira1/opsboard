"""Application and business-logic services.

Service modules coordinate repositories and models to implement opsboard's
operational workflows.
"""

from src.services.analytics_service import (
    AnalyticsError,
    AnalyticsService,
    InventorySummaryRow,
    SnapshotAlreadyExistsError,
    SnapshotNotFoundError,
)
from src.services.cache_service import (
    CacheError,
    CacheSerializationError,
    CacheService,
)
from src.services.dashboard_service import (
    DashboardService,
    InventoryDashboard,
    OrderDashboard,
    ReservationDashboard,
    SnapshotDashboard,
)
from src.services.event_service import EventService
from src.services.export_service import ExportService
from src.services.import_service import (
    BulkImportError,
    ImportService,
    InvalidImportQuantityError,
    MalformedCsvError,
    StockImportRow,
    UnknownProductError,
    UnknownWarehouseError,
)
from src.services.inventory_service import (
    InventoryError,
    InventoryService,
    NegativeStockError,
    ProductNotFoundError,
    WarehouseNotFoundError,
)
from src.services.notification_service import (
    InvalidNotificationStateError,
    NotificationError,
    NotificationNotFoundError,
    NotificationService,
)
from src.services.report_job_service import (
    InvalidReportJobStateError,
    ReportJobError,
    ReportJobNotFoundError,
    ReportJobService,
    ReportRequestNotFoundError,
)
from src.services.scheduler_service import (
    InvalidScheduledJobStateError,
    ScheduledJobNotFoundError,
    SchedulerError,
    SchedulerExecutionError,
    SchedulerService,
)
from src.services.order_service import (
    DuplicateOrderReferenceError,
    EmptyOrderError,
    InactiveReservationError,
    InvalidOrderStateError,
    OrderError,
    OrderLine,
    OrderNotFoundError,
    OrderQuantityMismatchError,
    OrderService,
)
from src.services.reservation_service import (
    InsufficientAvailableStockError,
    InvalidReservationQuantityError,
    ReservationAlreadyFulfilledError,
    ReservationAlreadyReleasedError,
    ReservationError,
    ReservationNotFoundError,
    ReservationService,
)

__all__ = [
    "AnalyticsError",
    "AnalyticsService",
    "BulkImportError",
    "CacheError",
    "CacheSerializationError",
    "CacheService",
    "DashboardService",
    "DuplicateOrderReferenceError",
    "EmptyOrderError",
    "EventService",
    "ExportService",
    "ImportService",
    "InactiveReservationError",
    "InsufficientAvailableStockError",
    "InvalidImportQuantityError",
    "InvalidNotificationStateError",
    "InvalidOrderStateError",
    "InvalidReportJobStateError",
    "InvalidReservationQuantityError",
    "InvalidScheduledJobStateError",
    "InventoryDashboard",
    "InventoryError",
    "InventoryService",
    "InventorySummaryRow",
    "MalformedCsvError",
    "NegativeStockError",
    "NotificationError",
    "NotificationNotFoundError",
    "NotificationService",
    "OrderDashboard",
    "OrderError",
    "OrderLine",
    "OrderNotFoundError",
    "OrderQuantityMismatchError",
    "OrderService",
    "ProductNotFoundError",
    "ReportJobError",
    "ReportJobNotFoundError",
    "ReportJobService",
    "ReportRequestNotFoundError",
    "ReservationAlreadyFulfilledError",
    "ReservationAlreadyReleasedError",
    "ReservationDashboard",
    "ReservationError",
    "ReservationNotFoundError",
    "ReservationService",
    "ScheduledJobNotFoundError",
    "SchedulerError",
    "SchedulerExecutionError",
    "SchedulerService",
    "SnapshotAlreadyExistsError",
    "SnapshotDashboard",
    "SnapshotNotFoundError",
    "StockImportRow",
    "UnknownProductError",
    "UnknownWarehouseError",
    "WarehouseNotFoundError",
]
