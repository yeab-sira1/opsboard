"""Filter specification for in-memory filtering."""

from __future__ import annotations

import uuid
from datetime import date

from src.models import OrderStatus, ReservationStatus
from src.value_objects import DateRange


class FilterSpec:
    """Reusable filter specification for matching items against criteria."""

    def __init__(
        self,
        product_ids: list[uuid.UUID] | None = None,
        warehouse_ids: list[uuid.UUID] | None = None,
        order_statuses: list[OrderStatus] | None = None,
        reservation_statuses: list[ReservationStatus] | None = None,
        report_types: list[str] | None = None,
        date_range: DateRange | None = None,
        search_text: str | None = None,
    ) -> None:
        self._product_ids = set(product_ids or [])
        self._warehouse_ids = set(warehouse_ids or [])
        self._order_statuses = set(order_statuses or [])
        self._reservation_statuses = set(reservation_statuses or [])
        self._report_types = set(report_types or [])
        self._date_range = date_range
        self._search_text = (search_text or "").lower()

    def matches_product(self, product_id: uuid.UUID) -> bool:
        """Check if product_id matches filter (or filter not applied)."""
        if not self._product_ids:
            return True
        return product_id in self._product_ids

    def matches_warehouse(self, warehouse_id: uuid.UUID) -> bool:
        """Check if warehouse_id matches filter (or filter not applied)."""
        if not self._warehouse_ids:
            return True
        return warehouse_id in self._warehouse_ids

    def matches_order_status(self, status: OrderStatus) -> bool:
        """Check if order status matches filter (or filter not applied)."""
        if not self._order_statuses:
            return True
        return status in self._order_statuses

    def matches_reservation_status(self, status: ReservationStatus) -> bool:
        """Check if reservation status matches filter (or filter not applied)."""
        if not self._reservation_statuses:
            return True
        return status in self._reservation_statuses

    def matches_report_type(self, report_type: str) -> bool:
        """Check if report type matches filter (or filter not applied)."""
        if not self._report_types:
            return True
        return report_type in self._report_types

    def matches_date(self, target_date: date) -> bool:
        """Check if date matches filter (or filter not applied)."""
        if self._date_range is None:
            return True
        return self._date_range.contains(target_date)

    def matches_text(self, text: str) -> bool:
        """Check if text contains search term (or filter not applied)."""
        if not self._search_text:
            return True
        return self._search_text in text.lower()
