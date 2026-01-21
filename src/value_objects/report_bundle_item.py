"""Report bundle item value object."""

from __future__ import annotations


class ReportBundleItem:
    """An immutable report item specification in a bundle."""

    def __init__(self, report_type: str, parameters_json: str | None = None) -> None:
        if not report_type:
            raise ValueError("report_type must not be empty")
        self._report_type = report_type
        self._parameters_json = parameters_json or ""

    @property
    def report_type(self) -> str:
        """The type of report (e.g., 'inventory', 'orders')."""
        return self._report_type

    @property
    def parameters_json(self) -> str:
        """JSON parameters for the report."""
        return self._parameters_json

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ReportBundleItem):
            return NotImplemented
        return (
            self._report_type == other._report_type
            and self._parameters_json == other._parameters_json
        )

    def __repr__(self) -> str:
        return (
            f"ReportBundleItem(report_type={self._report_type!r}, "
            f"parameters_json={self._parameters_json!r})"
        )
