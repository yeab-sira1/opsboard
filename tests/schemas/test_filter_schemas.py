"""Tests for filter schemas."""

from datetime import date

import pytest

from src.models import OrderStatus, ReservationStatus
from src.schemas import FilterRequest, FilterResult
from src.value_objects import DateRange, Pagination, SortSpec


class TestFilterRequest:
    def test_empty_filter_request(self) -> None:
        req = FilterRequest()
        assert req.is_empty()

    def test_filter_with_search_text(self) -> None:
        req = FilterRequest(search_text="widget")
        assert not req.is_empty()
        assert req.search_text == "widget"

    def test_filter_with_date_range(self) -> None:
        dr = DateRange(date(2025, 1, 1), date(2025, 12, 31))
        req = FilterRequest(date_range=dr)
        assert not req.is_empty()
        assert req.date_range == dr

    def test_filter_with_order_statuses(self) -> None:
        req = FilterRequest(order_statuses=[OrderStatus.PENDING])
        assert not req.is_empty()

    def test_filter_with_pagination_and_sort(self) -> None:
        pagination = Pagination(page=2, page_size=50)
        sort = SortSpec("created_at", ascending=False)
        req = FilterRequest(pagination=pagination, sort_spec=sort)
        assert req.pagination == pagination
        assert req.sort_spec == sort

    def test_combined_filters(self) -> None:
        dr = DateRange(date(2025, 1, 1), date(2025, 6, 30))
        pagination = Pagination(page=1, page_size=25)
        sort = SortSpec("name")
        req = FilterRequest(
            search_text="item",
            date_range=dr,
            order_statuses=[OrderStatus.COMPLETED],
            pagination=pagination,
            sort_spec=sort,
        )
        assert not req.is_empty()
        assert req.search_text == "item"
        assert req.date_range == dr
        assert req.order_statuses == [OrderStatus.COMPLETED]
        assert req.pagination == pagination
        assert req.sort_spec == sort


class TestFilterResult:
    def test_empty_result(self) -> None:
        result: FilterResult[str] = FilterResult(
            items=[], total_count=0, page=1, page_size=20
        )
        assert result.items == []
        assert result.total_count == 0
        assert not result.has_next

    def test_single_page_result(self) -> None:
        result: FilterResult[int] = FilterResult(
            items=[1, 2, 3], total_count=3, page=1, page_size=20
        )
        assert result.items == [1, 2, 3]
        assert result.total_count == 3
        assert not result.has_next

    def test_first_of_multiple_pages(self) -> None:
        result: FilterResult[int] = FilterResult(
            items=list(range(20)), total_count=55, page=1, page_size=20
        )
        assert len(result.items) == 20
        assert result.total_count == 55
        assert result.has_next

    def test_middle_page(self) -> None:
        result: FilterResult[int] = FilterResult(
            items=list(range(20, 40)), total_count=100, page=2, page_size=20
        )
        assert result.has_next

    def test_last_page(self) -> None:
        result: FilterResult[int] = FilterResult(
            items=[80, 81, 82, 83], total_count=84, page=5, page_size=20
        )
        assert not result.has_next

    def test_exact_page_boundary(self) -> None:
        result: FilterResult[int] = FilterResult(
            items=list(range(60, 80)), total_count=100, page=5, page_size=20
        )
        assert not result.has_next
