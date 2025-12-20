"""SQLAlchemy ORM models for opsboard.

Importing this package registers every model with the shared declarative
``Base`` so that ``Base.metadata`` is complete and inter-model relationships
resolve correctly.
"""

from src.models.base import Base
from src.models.cache_entry import CacheEntry
from src.models.daily_inventory_snapshot import DailyInventorySnapshot
from src.models.domain_event import DomainEvent, DomainEventType
from src.models.import_job import ImportJob, ImportJobStatus
from src.models.notification import Notification, NotificationStatus
from src.models.order import Order, OrderStatus
from src.models.order_item import OrderItem
from src.models.organization import Organization
from src.models.product import Product
from src.models.report_job import ReportJob, ReportJobStatus
from src.models.report_request import ReportRequest, ReportType
from src.models.reservation import Reservation, ReservationStatus
from src.models.role import Role
from src.models.scheduled_job import ScheduledJob, ScheduledJobStatus
from src.models.stock_record import StockRecord
from src.models.user import User
from src.models.warehouse import Warehouse

__all__ = [
    "Base",
    "CacheEntry",
    "DailyInventorySnapshot",
    "DomainEvent",
    "DomainEventType",
    "ImportJob",
    "ImportJobStatus",
    "Notification",
    "NotificationStatus",
    "Order",
    "OrderItem",
    "OrderStatus",
    "Organization",
    "Product",
    "ReportJob",
    "ReportJobStatus",
    "ReportRequest",
    "ReportType",
    "Reservation",
    "ReservationStatus",
    "Role",
    "ScheduledJob",
    "ScheduledJobStatus",
    "StockRecord",
    "User",
    "Warehouse",
]
