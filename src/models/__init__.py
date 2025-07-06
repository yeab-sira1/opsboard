"""SQLAlchemy ORM models for opsboard.

Importing this package registers every model with the shared declarative
``Base`` so that ``Base.metadata`` is complete and inter-model relationships
resolve correctly.
"""

from src.models.base import Base
from src.models.organization import Organization
from src.models.product import Product
from src.models.reservation import Reservation, ReservationStatus
from src.models.role import Role
from src.models.stock_record import StockRecord
from src.models.user import User
from src.models.warehouse import Warehouse

__all__ = [
    "Base",
    "Organization",
    "Product",
    "Reservation",
    "ReservationStatus",
    "Role",
    "StockRecord",
    "User",
    "Warehouse",
]
