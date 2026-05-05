"""Workflow D: Retry policy → Failed job → Retry service → Scheduler → Success/failure outcomes."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy.orm import Session

from src.models import (
    DomainEventType,
    RetryPolicy,
    RetryStrategy,
    ScheduledJobStatus,
)
from src.schemas.retry_request import RetryRequest
from src.schemas.retry_result import RetryResult
from src.services import (
    EventService,
    RetryExhaustedError,
    RetryService,
    SchedulerService,
)
from src.value_objects import RetryConfig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_valid_job(scheduler: SchedulerService, name: str = "nightly-valid"):
    """Create a PENDING job with a non-empty name (will succeed when run)."""
    return scheduler.create_job(name, datetime(2026, 1, 1, tzinfo=timezone.utc))


def _make_failing_job(scheduler: SchedulerService):
    """Create a PENDING job with an empty name (will always fail when run)."""
    return scheduler.create_job("   ", datetime(2026, 1, 1, tzinfo=timezone.utc))


# ---------------------------------------------------------------------------
# Test 1 — full success path
# ---------------------------------------------------------------------------


def test_retry_full_success_path(session: Session) -> None:
    """A failed valid job is retried successfully; RETRY_SUCCEEDED event recorded."""
    scheduler_svc = SchedulerService(session)
    retry_svc = RetryService(session)
    event_svc = EventService(session)

    # Arrange: create a valid job and manually fail it
    job = _make_valid_job(scheduler_svc)
    scheduler_svc.fail_job(job.id, "simulated failure")
    assert job.status is ScheduledJobStatus.FAILED

    config = RetryConfig(
        strategy=RetryStrategy.IMMEDIATE,
        max_attempts=3,
        base_delay_seconds=0,
    )

    # Act
    attempt = retry_svc.retry_job(job.id, config)

    # Assert attempt succeeded
    assert attempt.successful is True

    # Assert domain event
    succeeded_events = event_svc.get_events_by_type(DomainEventType.RETRY_SUCCEEDED)
    assert len(succeeded_events) == 1

    # Assert the job is now COMPLETED
    completed_jobs = scheduler_svc.get_jobs_by_status(ScheduledJobStatus.COMPLETED)
    assert any(j.id == job.id for j in completed_jobs)


# ---------------------------------------------------------------------------
# Test 2 — retry failure then eventual exhaustion (simplified)
# ---------------------------------------------------------------------------


def test_retry_failure_then_eventual_success(session: Session) -> None:
    """Two failed retries of an always-failing job; next_retry_at set after first, None after second."""
    scheduler_svc = SchedulerService(session)
    retry_svc = RetryService(session)
    event_svc = EventService(session)

    # Arrange: empty name → always fails
    job = _make_failing_job(scheduler_svc)
    scheduler_svc.fail_job(job.id, "initial failure")

    config = RetryConfig(
        strategy=RetryStrategy.LINEAR,
        max_attempts=2,
        base_delay_seconds=5,
    )

    # First retry (attempt 1 of 2): fails, next_retry_at set because 1 < 2
    attempt1 = retry_svc.retry_job(job.id, config)
    assert attempt1.successful is False
    assert attempt1.next_retry_at is not None

    failed_events = event_svc.get_events_by_type(DomainEventType.RETRY_FAILED)
    assert len(failed_events) == 1

    # Second retry (attempt 2 of 2): fails, next_retry_at is None because 2 == max_attempts
    attempt2 = retry_svc.retry_job(job.id, config)
    assert attempt2.successful is False
    assert attempt2.next_retry_at is None

    failed_events = event_svc.get_events_by_type(DomainEventType.RETRY_FAILED)
    assert len(failed_events) == 2

    # Third retry raises RetryExhaustedError
    with pytest.raises(RetryExhaustedError):
        retry_svc.retry_job(job.id, config)


# ---------------------------------------------------------------------------
# Test 3 — retry exhaustion raises correctly
# ---------------------------------------------------------------------------


def test_retry_exhaustion_raises_correctly(session: Session) -> None:
    """With max_attempts=1, second retry attempt raises RetryExhaustedError."""
    scheduler_svc = SchedulerService(session)
    retry_svc = RetryService(session)

    # Arrange: always-failing job
    job = _make_failing_job(scheduler_svc)
    scheduler_svc.fail_job(job.id, "initial failure")

    config = RetryConfig(
        strategy=RetryStrategy.IMMEDIATE,
        max_attempts=1,
        base_delay_seconds=0,
    )

    # First (and only) retry fails
    attempt = retry_svc.retry_job(job.id, config)
    assert attempt.successful is False

    # Verify exactly 1 attempt recorded
    attempts = retry_svc.get_attempts(job.id)
    assert len(attempts) == 1

    # Second attempt exceeds max → raises
    with pytest.raises(RetryExhaustedError):
        retry_svc.retry_job(job.id, config)


# ---------------------------------------------------------------------------
# Test 4 — retry with policy loaded from database
# ---------------------------------------------------------------------------


def test_retry_with_policy_from_database(session: Session) -> None:
    """RetryService.retry_job_with_policy uses a persisted RetryPolicy correctly."""
    scheduler_svc = SchedulerService(session)
    retry_svc = RetryService(session)
    event_svc = EventService(session)

    # Arrange: persist a RetryPolicy
    policy = RetryPolicy(
        name="ops-policy",
        strategy=RetryStrategy.EXPONENTIAL,
        max_attempts=3,
        base_delay_seconds=2,
    )
    session.add(policy)
    session.flush()

    # Create a valid job (will succeed on retry) and fail it
    job = _make_valid_job(scheduler_svc, name="ops-job")
    scheduler_svc.fail_job(job.id, "pre-test failure")

    request = RetryRequest(scheduled_job_id=job.id, policy_id=policy.id)

    # Act
    result = retry_svc.retry_job_with_policy(request)

    # Assert result shape
    assert isinstance(result, RetryResult)
    assert result.scheduled_job_id == job.id

    # Assert a domain event was emitted (succeeded because job name is valid)
    succeeded_events = event_svc.get_events_by_type(DomainEventType.RETRY_SUCCEEDED)
    failed_events = event_svc.get_events_by_type(DomainEventType.RETRY_FAILED)
    # Exactly one of the two should be non-empty
    total_retry_events = len(succeeded_events) + len(failed_events)
    assert total_retry_events == 1

    # Since the job name is valid, it should succeed
    assert result.successful is True
    assert len(succeeded_events) == 1


# ---------------------------------------------------------------------------
# Test 5 — complete retry cycle with events
# ---------------------------------------------------------------------------


def test_complete_retry_cycle_with_events(session: Session) -> None:
    """Two failed retries with max_attempts=2; 2 RETRY_FAILED events, 0 RETRY_SUCCEEDED, 3rd raises."""
    scheduler_svc = SchedulerService(session)
    retry_svc = RetryService(session)
    event_svc = EventService(session)

    # Arrange: always-failing job
    job = _make_failing_job(scheduler_svc)
    scheduler_svc.fail_job(job.id, "initial failure")

    config = RetryConfig(
        strategy=RetryStrategy.IMMEDIATE,
        max_attempts=2,
        base_delay_seconds=0,
    )

    # First retry: fails
    a1 = retry_svc.retry_job(job.id, config)
    assert a1.successful is False

    # Second retry: fails
    a2 = retry_svc.retry_job(job.id, config)
    assert a2.successful is False

    # Verify attempt records
    all_attempts = retry_svc.get_attempts(job.id)
    assert len(all_attempts) == 2

    # Verify domain events
    failed_events = event_svc.get_events_by_type(DomainEventType.RETRY_FAILED)
    assert len(failed_events) == 2

    succeeded_events = event_svc.get_events_by_type(DomainEventType.RETRY_SUCCEEDED)
    assert len(succeeded_events) == 0

    # Third retry raises RetryExhaustedError
    with pytest.raises(RetryExhaustedError):
        retry_svc.retry_job(job.id, config)
