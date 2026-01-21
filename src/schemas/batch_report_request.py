"""Batch report request schema."""

from __future__ import annotations

from typing import NamedTuple

from src.value_objects.report_bundle_item import ReportBundleItem


class BatchReportRequest(NamedTuple):
    """Specifies a batch of reports to generate."""

    items: list[ReportBundleItem]

    def is_empty(self) -> bool:
        """Check if there are no items."""
        return len(self.items) == 0
