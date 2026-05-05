"""Integration tests for RetryService.retry_job_with_policy and RetryPolicyRepository."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.orm import Session

from src.models.retry_policy import RetryPolicy, RetryStrategy
from src.models.scheduled_job import ScheduledJobStatus
from src.repositories import RetryPolicyRepository
from src.schemas.retry_request import RetryRequest
from src.schemas.retry_result import RetryResult
from src.services import (
    RetryExhaustedError,
    RetryPolicyNotFoundError,
    RetryService,
    SchedulerService,
)


def _at() -> datetime:
    return datetime(2026, 1, 1, tzinfo=timezone.utc)


def _make_policy(
    session: Session,
    *,
    name: str = "test-policy",
    strategy: RetryStrategy = RetryStrategy.LINEAR,
    max_attempts: int = 3,
    base_delay_seconds: int = 5,
) -> RetryPolicy:
    """Persist and return a RetryPolicy row."""
    repo = RetryPolicyRepository(session)
    return repo.add(
        RetryPolicy(
            name=name,
            strategy=strategy,
            max_attempts=max_attempts,
            base_delay_seconds=base_delay_seconds,
        )
    )


def _failing_job(scheduler: SchedulerService):
    """Create a job whose execution always fails (blank job_name triggers SchedulerExecutionError)."""
    job = scheduler.create_job("   ", _at())
    scheduler.run_job(job.id)
    assert job.status is ScheduledJobStatus.FAILED
    return job


def _succeeding_job(scheduler: SchedulerService):
    """Create a job whose execution will succeed (non-empty job_name)."""
    job = scheduler.create_job("nightly-report", _at())
    scheduler.run_job(job.id)
    assert job.status is ScheduledJobStatus.COMPLETED
    return job


# ---------------------------------------------------------------------------
# test_retry_job_with_policy_success_path
# ---------------------------------------------------------------------------

def test_retry_job_with_policy_success_path(session: Session) -> None:
    """A successfully retried job returns RetryResult with successful=True."""
    scheduler = SchedulerService(session)
    retry_svc = RetryService(session)

    policy = _make_policy(session, name="fast", max_attempts=3, base_delay_seconds=1)

    # Create a job that was manually failed — it will succeed on retry
    # because its job_name is non-empty.
    job = scheduler.create_job("nightly-report", _at())
    scheduler.fail_job(job.id, "transient network error")

    request = RetryRequest(scheduled_job_id=job.id, policy_id=policy.id)
    result = retry_svc.retry_job_with_policy(request)

    assert isinstance(result, RetryResult)
    assert result.successful is True
    assert result.attempt_number == 1
    assert result.scheduled_job_id == job.id


# ---------------------------------------------------------------------------
# test_retry_job_with_policy_exhausted
# ---------------------------------------------------------------------------

def test_retry_job_with_policy_exhausted(session: Session) -> None:
    """After max_attempts retries, retry_job_with_policy raises RetryExhaustedError."""
    scheduler = SchedulerService(session)
    retry_svc = RetryService(session)

    policy = _make_policy(
        session, name="strict", max_attempts=2, base_delay_seconds=0,
        strategy=RetryStrategy.IMMEDIATE,
    )

    job = _failing_job(scheduler)
    request = RetryRequest(scheduled_job_id=job.id, policy_id=policy.id)

    # First and second retries consume all allowed attempts.
    retry_svc.retry_job_with_policy(request)
    retry_svc.retry_job_with_policy(request)

    # Third call must raise.
    with pytest.raises(RetryExhaustedError) as exc_info:
        retry_svc.retry_job_with_policy(request)

    assert exc_info.value.scheduled_job_id == job.id
    assert exc_info.value.max_attempts == 2


# ---------------------------------------------------------------------------
# test_retry_job_with_missing_policy_raises
# ---------------------------------------------------------------------------

def test_retry_job_with_missing_policy_raises(session: Session) -> None:
    """Calling retry_job_with_policy with a nonexistent policy_id raises RetryPolicyNotFoundError."""
    scheduler = SchedulerService(session)
    retry_svc = RetryService(session)

    job = _failing_job(scheduler)
    nonexistent_policy_id = uuid.uuid4()
    request = RetryRequest(scheduled_job_id=job.id, policy_id=nonexistent_policy_id)

    with pytest.raises(RetryPolicyNotFoundError) as exc_info:
        retry_svc.retry_job_with_policy(request)

    assert exc_info.value.policy_id == nonexistent_policy_id


# ---------------------------------------------------------------------------
# test_retry_result_fields_populated
# ---------------------------------------------------------------------------

def test_retry_result_fields_populated(session: Session) -> None:
    """All RetryResult fields are populated correctly for a failed (non-exhausted) retry."""
    scheduler = SchedulerService(session)
    retry_svc = RetryService(session)

    # 3 attempts; a failing job means we'll have a next_retry_at on attempt 1.
    policy = _make_policy(
        session, name="detailed",
        strategy=RetryStrategy.EXPONENTIAL,
        max_attempts=3,
        base_delay_seconds=10,
    )

    job = _failing_job(scheduler)
    request = RetryRequest(scheduled_job_id=job.id, policy_id=policy.id)
    result = retry_svc.retry_job_with_policy(request)

    # Fields that must be present
    assert result.scheduled_job_id == job.id
    assert result.attempt_number == 1
    assert result.successful is False
    assert result.exhausted is False  # 2 attempts remain
    assert result.next_retry_at is not None  # backoff delay was calculated
    assert result.error_message is not None  # job recorded an error


def test_retry_result_exhausted_flag_set_on_last_attempt(session: Session) -> None:
    """The exhausted flag is True when the last allowed attempt also fails."""
    scheduler = SchedulerService(session)
    retry_svc = RetryService(session)

    policy = _make_policy(
        session, name="one-shot",
        strategy=RetryStrategy.IMMEDIATE,
        max_attempts=1,
        base_delay_seconds=0,
    )

    job = _failing_job(scheduler)
    request = RetryRequest(scheduled_job_id=job.id, policy_id=policy.id)
    result = retry_svc.retry_job_with_policy(request)

    assert result.successful is False
    assert result.exhausted is True
    assert result.next_retry_at is None  # no more retries scheduled


# ---------------------------------------------------------------------------
# test_retry_policy_repository_crud
# ---------------------------------------------------------------------------

def test_retry_policy_repository_crud(session: Session) -> None:
    """RetryPolicyRepository supports full CRUD and get_by_name lookup."""
    repo = RetryPolicyRepository(session)

    # Create
    policy = repo.add(
        RetryPolicy(
            name="crud-policy",
            strategy=RetryStrategy.EXPONENTIAL,
            max_attempts=5,
            base_delay_seconds=30,
        )
    )
    assert policy.id is not None
    assert policy.name == "crud-policy"
    assert policy.strategy is RetryStrategy.EXPONENTIAL
    assert policy.max_attempts == 5
    assert policy.base_delay_seconds == 30

    # Read by primary key
    fetched = repo.get(policy.id)
    assert fetched is not None
    assert fetched.id == policy.id

    # get_by_name — existing name
    by_name = repo.get_by_name("crud-policy")
    assert by_name is not None
    assert by_name.id == policy.id

    # get_by_name — missing name returns None
    assert repo.get_by_name("no-such-policy") is None

    # List
    all_policies = repo.list()
    assert any(p.id == policy.id for p in all_policies)

    # Delete
    repo.delete(policy)
    assert repo.get(policy.id) is None
    assert repo.get_by_name("crud-policy") is None
