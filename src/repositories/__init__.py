"""Persistence helpers built on the repository pattern."""

from src.repositories.base_repository import BaseRepository
from src.repositories.audit_entry_repository import AuditEntryRepository
from src.repositories.cache_repository import CacheRepository
from src.repositories.daily_inventory_snapshot_repository import (
    DailyInventorySnapshotRepository,
)
from src.repositories.domain_event_repository import DomainEventRepository
from src.repositories.import_job_repository import ImportJobRepository
from src.repositories.notification_category_repository import (
    NotificationCategoryRepository,
)
from src.repositories.notification_preference_repository import (
    NotificationPreferenceRepository,
)
from src.repositories.notification_repository import NotificationRepository
from src.repositories.notification_template_repository import (
    NotificationTemplateRepository,
)
from src.repositories.order_repository import OrderRepository
from src.repositories.product_repository import ProductRepository
from src.repositories.report_bundle_repository import ReportBundleRepository
from src.repositories.report_job_repository import ReportJobRepository
from src.repositories.report_request_repository import ReportRequestRepository
from src.repositories.reservation_repository import ReservationRepository
from src.repositories.retry_attempt_repository import RetryAttemptRepository
from src.repositories.retry_policy_repository import RetryPolicyRepository
from src.repositories.scheduled_job_repository import ScheduledJobRepository
from src.repositories.stock_record_repository import StockRecordRepository
from src.repositories.warehouse_repository import WarehouseRepository
from src.repositories.workflow_execution_repository import (
    WorkflowExecutionRepository,
)

__all__ = [
    "BaseRepository",
    "AuditEntryRepository",
    "CacheRepository",
    "DailyInventorySnapshotRepository",
    "DomainEventRepository",
    "ImportJobRepository",
    "NotificationCategoryRepository",
    "NotificationPreferenceRepository",
    "NotificationRepository",
    "NotificationTemplateRepository",
    "OrderRepository",
    "ProductRepository",
    "ReportBundleRepository",
    "ReportJobRepository",
    "ReportRequestRepository",
    "ReservationRepository",
    "RetryAttemptRepository",
    "RetryPolicyRepository",
    "ScheduledJobRepository",
    "StockRecordRepository",
    "WarehouseRepository",
    "WorkflowExecutionRepository",
]
