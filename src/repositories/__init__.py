"""Persistence helpers built on the repository pattern."""

from src.repositories.base_repository import BaseRepository
from src.repositories.cache_repository import CacheRepository
from src.repositories.daily_inventory_snapshot_repository import (
    DailyInventorySnapshotRepository,
)
from src.repositories.domain_event_repository import DomainEventRepository
from src.repositories.notification_repository import NotificationRepository
from src.repositories.order_repository import OrderRepository
from src.repositories.product_repository import ProductRepository
from src.repositories.report_job_repository import ReportJobRepository
from src.repositories.report_request_repository import ReportRequestRepository
from src.repositories.reservation_repository import ReservationRepository
from src.repositories.scheduled_job_repository import ScheduledJobRepository
from src.repositories.stock_record_repository import StockRecordRepository
from src.repositories.warehouse_repository import WarehouseRepository

__all__ = [
    "BaseRepository",
    "CacheRepository",
    "DailyInventorySnapshotRepository",
    "DomainEventRepository",
    "NotificationRepository",
    "OrderRepository",
    "ProductRepository",
    "ReportJobRepository",
    "ReportRequestRepository",
    "ReservationRepository",
    "ScheduledJobRepository",
    "StockRecordRepository",
    "WarehouseRepository",
]
