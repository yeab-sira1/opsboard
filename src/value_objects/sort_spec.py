"""Sort specification value object."""

from __future__ import annotations


class SortSpec:
    """Specifies how to sort results by a field."""

    def __init__(self, field: str, ascending: bool = True) -> None:
        if not field:
            raise ValueError("field must not be empty")
        self._field = field
        self._ascending = ascending

    @property
    def field(self) -> str:
        """The field to sort by."""
        return self._field

    @property
    def ascending(self) -> bool:
        """True for ascending order, False for descending."""
        return self._ascending

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SortSpec):
            return NotImplemented
        return (
            self._field == other._field
            and self._ascending == other._ascending
        )

    def __repr__(self) -> str:
        direction = "ASC" if self._ascending else "DESC"
        return f"SortSpec(field={self._field!r}, {direction})"
