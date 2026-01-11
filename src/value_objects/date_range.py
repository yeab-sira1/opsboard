"""Date range value object."""

from __future__ import annotations

from datetime import date


class DateRange:
    """An inclusive date range from start to end."""

    def __init__(self, start_date: date, end_date: date) -> None:
        if start_date > end_date:
            raise ValueError(
                f"start_date ({start_date}) must be <= end_date ({end_date})"
            )
        self._start_date = start_date
        self._end_date = end_date

    @property
    def start_date(self) -> date:
        """The start of the range (inclusive)."""
        return self._start_date

    @property
    def end_date(self) -> date:
        """The end of the range (inclusive)."""
        return self._end_date

    def contains(self, target: date) -> bool:
        """Check if a date falls within this range."""
        return self._start_date <= target <= self._end_date

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, DateRange):
            return NotImplemented
        return (
            self._start_date == other._start_date
            and self._end_date == other._end_date
        )

    def __repr__(self) -> str:
        return (
            f"DateRange(start_date={self._start_date!r}, "
            f"end_date={self._end_date!r})"
        )
