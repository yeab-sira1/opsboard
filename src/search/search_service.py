"""Search service for filtering and querying entities."""

from __future__ import annotations

from typing import Generic, TypeVar

from src.models import Order, Reservation
from src.schemas import FilterRequest, FilterResult
from src.search.filter_spec import FilterSpec
from src.search.query_filter import QueryFilter
from src.services import (
    AnalyticsService,
    OrderService,
    ReservationService,
)
from src.value_objects import Pagination

T = TypeVar("T")


class SearchService:
    """Searches and filters orders, reservations, and inventory in memory."""

    def __init__(
        self,
        orders_service: OrderService,
        reservations_service: ReservationService,
        analytics_service: AnalyticsService,
    ) -> None:
        self._orders = orders_service
        self._reservations = reservations_service
        self._analytics = analytics_service

    def search_orders(
        self, request: FilterRequest
    ) -> FilterResult[Order]:
        """Search orders with filtering, sorting, and pagination."""
        items = self._orders.get_all_orders()
        spec = FilterSpec(
            product_ids=request.product_ids,
            warehouse_ids=request.warehouse_ids,
            order_statuses=request.order_statuses,
            date_range=request.date_range,
            search_text=request.search_text,
        )

        filtered = QueryFilter.apply_filter(
            items,
            spec,
            lambda order: (
                spec.matches_order_status(order.status)
                and (
                    not spec._search_text
                    or spec.matches_text(order.reference or "")
                )
                and (
                    not spec._date_range
                    or spec.matches_date(order.created_at.date())
                )
            ),
        )

        sorted_items = QueryFilter.apply_sort(
            filtered,
            request.sort_spec,
            lambda order: getattr(
                order, request.sort_spec.field if request.sort_spec else "id"
            ),
        )

        pagination = request.pagination or Pagination()
        total_count = len(sorted_items)
        paginated = QueryFilter.apply_pagination(
            sorted_items, pagination.offset, pagination.limit
        )

        return FilterResult(
            items=paginated,
            total_count=total_count,
            page=pagination.page,
            page_size=pagination.page_size,
        )

    def search_reservations(
        self, request: FilterRequest
    ) -> FilterResult[Reservation]:
        """Search reservations with filtering, sorting, and pagination."""
        items = self._reservations.get_all_reservations()
        spec = FilterSpec(
            product_ids=request.product_ids,
            warehouse_ids=request.warehouse_ids,
            reservation_statuses=request.reservation_statuses,
            date_range=request.date_range,
            search_text=request.search_text,
        )

        filtered = QueryFilter.apply_filter(
            items,
            spec,
            lambda res: (
                spec.matches_reservation_status(res.status)
                and (
                    not spec._search_text
                    or spec.matches_text(res.order_reference or "")
                )
                and (
                    not spec._date_range
                    or spec.matches_date(res.created_at.date())
                )
            ),
        )

        sorted_items = QueryFilter.apply_sort(
            filtered,
            request.sort_spec,
            lambda res: getattr(
                res, request.sort_spec.field if request.sort_spec else "id"
            ),
        )

        pagination = request.pagination or Pagination()
        total_count = len(sorted_items)
        paginated = QueryFilter.apply_pagination(
            sorted_items, pagination.offset, pagination.limit
        )

        return FilterResult(
            items=paginated,
            total_count=total_count,
            page=pagination.page,
            page_size=pagination.page_size,
        )

    def search_inventory(
        self, request: FilterRequest
    ) -> FilterResult[dict]:
        """Search inventory with filtering, sorting, and pagination."""
        summary_rows = self._analytics.get_inventory_summary()
        items = [
            {
                "product_id": row.product_id,
                "warehouse_id": row.warehouse_id,
                "physical_stock": row.physical_stock,
                "reserved_quantity": row.reserved_quantity,
                "available_stock": row.available_stock,
            }
            for row in summary_rows
        ]
        if not items:
            return FilterResult(
                items=[], total_count=0, page=1, page_size=20
            )

        spec = FilterSpec(
            product_ids=request.product_ids,
            warehouse_ids=request.warehouse_ids,
            date_range=request.date_range,
            search_text=request.search_text,
        )

        filtered = QueryFilter.apply_filter(
            items,
            spec,
            lambda inv: (
                spec.matches_product(inv["product_id"])
                and spec.matches_warehouse(inv["warehouse_id"])
            ),
        )

        sorted_items = QueryFilter.apply_sort(
            filtered,
            request.sort_spec,
            lambda inv: inv.get(
                request.sort_spec.field if request.sort_spec else "id", ""
            ),
        )

        pagination = request.pagination or Pagination()
        total_count = len(sorted_items)
        paginated = QueryFilter.apply_pagination(
            sorted_items, pagination.offset, pagination.limit
        )

        return FilterResult(
            items=paginated,
            total_count=total_count,
            page=pagination.page,
            page_size=pagination.page_size,
        )
