"""Filter result schema."""

from __future__ import annotations

from typing import Generic, NamedTuple, TypeVar

T = TypeVar("T")


class FilterResult(NamedTuple, Generic[T]):
    """Immutable search result with pagination info."""

    items: list[T]
    total_count: int
    page: int
    page_size: int

    @property
    def has_next(self) -> bool:
        """Check if there are more pages."""
        total_pages = (self.total_count + self.page_size - 1) // self.page_size
        return self.page < total_pages
