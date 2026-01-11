"""Filter request schema."""

from __future__ import annotations

import uuid
from typing import NamedTuple

from src.models import OrderStatus, ReservationStatus
from src.value_objects import DateRange, Pagination, SortSpec


class FilterRequest(NamedTuple):
    """Specifies filters, sorting, and pagination for a search."""

    product_ids: list[uuid.UUID] | None = None
    warehouse_ids: list[uuid.UUID] | None = None
    order_statuses: list[OrderStatus] | None = None
    reservation_statuses: list[ReservationStatus] | None = None
    report_types: list[str] | None = None
    date_range: DateRange | None = None
    sort_spec: SortSpec | None = None
    pagination: Pagination | None = None
    search_text: str | None = None

    def is_empty(self) -> bool:
        """Check if all filter fields are None."""
        return all(
            v is None
            for v in (
                self.product_ids,
                self.warehouse_ids,
                self.order_statuses,
                self.reservation_statuses,
                self.report_types,
                self.date_range,
                self.search_text,
            )
        )
