"""SQLAlchemy ORM models for opsboard.

Importing this package registers every model with the shared declarative
``Base`` so that ``Base.metadata`` is complete and inter-model relationships
resolve correctly.
"""

from src.models.base import Base
from src.models.daily_inventory_snapshot import DailyInventorySnapshot
from src.models.notification import Notification, NotificationStatus
from src.models.order import Order, OrderStatus
from src.models.order_item import OrderItem
from src.models.organization import Organization
from src.models.product import Product
from src.models.report_job import ReportJob, ReportJobStatus
from src.models.report_request import ReportRequest, ReportType
from src.models.reservation import Reservation, ReservationStatus
from src.models.role import Role
from src.models.stock_record import StockRecord
from src.models.user import User
from src.models.warehouse import Warehouse

__all__ = [
    "Base",
    "DailyInventorySnapshot",
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
    "StockRecord",
    "User",
    "Warehouse",
]
