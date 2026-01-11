"""Pagination value object."""

from __future__ import annotations


class Pagination:
    """Represents a page and page size for pagination."""

    def __init__(self, page: int = 1, page_size: int = 20) -> None:
        if page < 1:
            raise ValueError(f"page must be >= 1, got {page}")
        if page_size <= 0:
            raise ValueError(f"page_size must be > 0, got {page_size}")
        self._page = page
        self._page_size = page_size

    @property
    def page(self) -> int:
        """The current page number (1-indexed)."""
        return self._page

    @property
    def page_size(self) -> int:
        """The number of items per page."""
        return self._page_size

    @property
    def offset(self) -> int:
        """The number of items to skip (0-indexed)."""
        return (self._page - 1) * self._page_size

    @property
    def limit(self) -> int:
        """The maximum number of items to retrieve."""
        return self._page_size

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Pagination):
            return NotImplemented
        return (
            self._page == other._page
            and self._page_size == other._page_size
        )

    def __repr__(self) -> str:
        return (
            f"Pagination(page={self._page}, page_size={self._page_size})"
        )
