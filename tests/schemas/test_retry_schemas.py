"""Tests for retry request/result schemas."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from src.schemas import RetryRequest, RetryResult


def test_retry_request_fields() -> None:
    job_id = uuid.uuid4()
    policy_id = uuid.uuid4()
    req = RetryRequest(scheduled_job_id=job_id, policy_id=policy_id)
    assert req.scheduled_job_id == job_id
    assert req.policy_id == policy_id


def test_retry_result_defaults() -> None:
    job_id = uuid.uuid4()
    result = RetryResult(
        scheduled_job_id=job_id,
        attempt_number=1,
        successful=False,
        exhausted=False,
    )
    assert result.next_retry_at is None
    assert result.error_message is None


def test_retry_result_full() -> None:
    when = datetime(2026, 1, 1, tzinfo=timezone.utc)
    result = RetryResult(
        scheduled_job_id=uuid.uuid4(),
        attempt_number=2,
        successful=True,
        exhausted=True,
        next_retry_at=when,
        error_message="boom",
    )
    assert result.successful is True
    assert result.exhausted is True
    assert result.next_retry_at == when
