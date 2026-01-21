"""Batch report result schema."""

from __future__ import annotations

from typing import NamedTuple


class BatchReportResult(NamedTuple):
    """Result of batch report generation."""

    results: dict[str, dict]
    generated_count: int
    failed_count: int

    @property
    def total_count(self) -> int:
        """Total number of reports attempted."""
        return self.generated_count + self.failed_count

    @property
    def all_succeeded(self) -> bool:
        """Check if all reports succeeded."""
        return self.failed_count == 0
