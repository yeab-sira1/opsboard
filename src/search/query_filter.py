"""Query filtering logic."""

from __future__ import annotations

from typing import Callable, TypeVar

from src.search.filter_spec import FilterSpec
from src.value_objects import SortSpec

T = TypeVar("T")


class QueryFilter:
    """Applies filtering, sorting, and pagination to sequences in memory."""

    @staticmethod
    def apply_filter(
        items: list[T], spec: FilterSpec, predicate: Callable[[T], bool]
    ) -> list[T]:
        """Filter items using the spec and a predicate."""
        return [item for item in items if predicate(item)]

    @staticmethod
    def apply_sort(
        items: list[T],
        sort_spec: SortSpec | None,
        key_func: Callable[[T], object],
    ) -> list[T]:
        """Sort items by sort_spec using key_func to extract sort values."""
        if sort_spec is None:
            return items
        return sorted(items, key=key_func, reverse=not sort_spec.ascending)

    @staticmethod
    def apply_pagination(
        items: list[T], offset: int, limit: int
    ) -> list[T]:
        """Apply pagination using offset and limit."""
        return items[offset : offset + limit]
