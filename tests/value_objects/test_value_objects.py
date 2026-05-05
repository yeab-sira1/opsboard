"""Tests for value objects."""

import pytest
from datetime import date

from src.value_objects import DateRange, Pagination, SortSpec


class TestDateRange:
    def test_valid_range(self) -> None:
        dr = DateRange(date(2025, 1, 1), date(2025, 12, 31))
        assert dr.start_date == date(2025, 1, 1)
        assert dr.end_date == date(2025, 12, 31)

    def test_same_start_and_end(self) -> None:
        dr = DateRange(date(2025, 6, 15), date(2025, 6, 15))
        assert dr.start_date == dr.end_date

    def test_rejects_inverted_range(self) -> None:
        with pytest.raises(ValueError, match="start_date.*must be"):
            DateRange(date(2025, 12, 31), date(2025, 1, 1))

    def test_contains(self) -> None:
        dr = DateRange(date(2025, 1, 1), date(2025, 12, 31))
        assert dr.contains(date(2025, 6, 15))
        assert dr.contains(date(2025, 1, 1))
        assert dr.contains(date(2025, 12, 31))
        assert not dr.contains(date(2024, 12, 31))
        assert not dr.contains(date(2026, 1, 1))

    def test_equality(self) -> None:
        dr1 = DateRange(date(2025, 1, 1), date(2025, 12, 31))
        dr2 = DateRange(date(2025, 1, 1), date(2025, 12, 31))
        dr3 = DateRange(date(2025, 1, 1), date(2025, 6, 30))
        assert dr1 == dr2
        assert dr1 != dr3


class TestSortSpec:
    def test_ascending_sort(self) -> None:
        spec = SortSpec("created_at", ascending=True)
        assert spec.field == "created_at"
        assert spec.ascending is True

    def test_descending_sort(self) -> None:
        spec = SortSpec("created_at", ascending=False)
        assert spec.field == "created_at"
        assert spec.ascending is False

    def test_default_ascending(self) -> None:
        spec = SortSpec("name")
        assert spec.ascending is True

    def test_rejects_empty_field(self) -> None:
        with pytest.raises(ValueError, match="field must not be empty"):
            SortSpec("")

    def test_equality(self) -> None:
        spec1 = SortSpec("name", ascending=True)
        spec2 = SortSpec("name", ascending=True)
        spec3 = SortSpec("name", ascending=False)
        assert spec1 == spec2
        assert spec1 != spec3

    def test_not_equal_to_different_type(self) -> None:
        spec = SortSpec("name")
        assert spec.__eq__("not-a-spec") is NotImplemented

    def test_repr_ascending(self) -> None:
        spec = SortSpec("price", ascending=True)
        r = repr(spec)
        assert "price" in r
        assert "ASC" in r

    def test_repr_descending(self) -> None:
        spec = SortSpec("price", ascending=False)
        r = repr(spec)
        assert "price" in r
        assert "DESC" in r


class TestPagination:
    def test_valid_pagination(self) -> None:
        p = Pagination(page=2, page_size=25)
        assert p.page == 2
        assert p.page_size == 25
        assert p.offset == 25
        assert p.limit == 25

    def test_first_page_offset(self) -> None:
        p = Pagination(page=1, page_size=10)
        assert p.offset == 0

    def test_default_values(self) -> None:
        p = Pagination()
        assert p.page == 1
        assert p.page_size == 20

    def test_rejects_zero_page(self) -> None:
        with pytest.raises(ValueError, match="page must be >= 1"):
            Pagination(page=0)

    def test_rejects_negative_page(self) -> None:
        with pytest.raises(ValueError, match="page must be >= 1"):
            Pagination(page=-1)

    def test_rejects_zero_page_size(self) -> None:
        with pytest.raises(ValueError, match="page_size must be > 0"):
            Pagination(page_size=0)

    def test_rejects_negative_page_size(self) -> None:
        with pytest.raises(ValueError, match="page_size must be > 0"):
            Pagination(page_size=-5)

    def test_equality(self) -> None:
        p1 = Pagination(page=1, page_size=20)
        p2 = Pagination(page=1, page_size=20)
        p3 = Pagination(page=2, page_size=20)
        assert p1 == p2
        assert p1 != p3
