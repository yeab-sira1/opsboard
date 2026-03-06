"""Retry request schema."""

from __future__ import annotations

import uuid
from typing import NamedTuple


class RetryRequest(NamedTuple):
    """A request to retry a scheduled job under a retry policy."""

    scheduled_job_id: uuid.UUID
    policy_id: uuid.UUID
