"""SQLAlchemy ORM models for opsboard.

Importing this package registers every model with the shared declarative
``Base`` so that ``Base.metadata`` is complete and inter-model relationships
resolve correctly.
"""

from src.models.base import Base
from src.models.audit_entry import AuditEntry
from src.models.cache_entry import CacheEntry
from src.models.daily_inventory_snapshot import DailyInventorySnapshot
from src.models.domain_event import DomainEvent, DomainEventType
from src.models.import_job import ImportJob, ImportJobStatus
from src.models.notification import Notification, NotificationStatus
from src.models.notification_category import NotificationCategory
from src.models.notification_preference import NotificationPreference
from src.models.notification_template import NotificationTemplate
from src.models.order import Order, OrderStatus
from src.models.order_item import OrderItem
from src.models.organization import Organization
from src.models.product import Product
from src.models.report_bundle import ReportBundle
from src.models.report_job import ReportJob, ReportJobStatus
from src.models.report_request import ReportRequest, ReportType
from src.models.reservation import Reservation, ReservationStatus
from src.models.retry_attempt import RetryAttempt
from src.models.retry_policy import RetryPolicy, RetryStrategy
from src.models.role import Role
from src.models.scheduled_job import ScheduledJob, ScheduledJobStatus
from src.models.stock_record import StockRecord
from src.models.user import User
from src.models.warehouse import Warehouse
from src.models.workflow_execution import WorkflowExecution, WorkflowStatus

__all__ = [
    "Base",
    "AuditEntry",
    "CacheEntry",
    "DailyInventorySnapshot",
    "DomainEvent",
    "DomainEventType",
    "ImportJob",
    "ImportJobStatus",
    "Notification",
    "NotificationCategory",
    "NotificationPreference",
    "NotificationStatus",
    "NotificationTemplate",
    "Order",
    "OrderItem",
    "OrderStatus",
    "Organization",
    "Product",
    "ReportBundle",
    "ReportJob",
    "ReportJobStatus",
    "ReportRequest",
    "ReportType",
    "Reservation",
    "ReservationStatus",
    "RetryAttempt",
    "RetryPolicy",
    "RetryStrategy",
    "Role",
    "ScheduledJob",
    "ScheduledJobStatus",
    "StockRecord",
    "User",
    "Warehouse",
    "WorkflowExecution",
    "WorkflowStatus",
]
