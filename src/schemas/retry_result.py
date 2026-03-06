"""Retry result schema."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import NamedTuple


class RetryResult(NamedTuple):
    """The outcome of a retry operation."""

    scheduled_job_id: uuid.UUID
    attempt_number: int
    successful: bool
    exhausted: bool
    next_retry_at: datetime | None = None
    error_message: str | None = None
