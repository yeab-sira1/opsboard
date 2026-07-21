"""Centralized exception hierarchy for opsboard.

All application exceptions ultimately inherit from :class:`OpsboardError`,
making it easy to catch any opsboard-specific error at a broad boundary without
accidentally swallowing unrelated Python exceptions.

Domain-grouped sub-hierarchies live in sibling modules and are re-exported
here so callers can import from a single location::

    from src.exceptions import OpsboardError, NotFoundError, ConflictError

Services keep their own local aliases that inherit from this hierarchy; the
public names they already export remain unchanged.
"""

from src.exceptions.base import OpsboardError
from src.exceptions.lookup import NotFoundError
from src.exceptions.state import ConflictError, InvalidStateError
from src.exceptions.validation import ValidationError

__all__ = [
    "OpsboardError",
    # broad semantic groups callers can catch
    "ConflictError",
    "InvalidStateError",
    "NotFoundError",
    "ValidationError",
]
