"""Retry service: bounded, synchronous re-execution of scheduled jobs."""

from __future__ import annotations

import uuid
from datetime import timedelta

from sqlalchemy.orm import Session

from src.exceptions.base import OpsboardError
from src.exceptions.lookup import NotFoundError
from src.exceptions.state import InvalidStateError
from src.models.base import utcnow
from src.models.domain_event import DomainEventType
from src.models.retry_attempt import RetryAttempt
from src.models.scheduled_job import ScheduledJobStatus
from src.repositories import RetryAttemptRepository, RetryPolicyRepository
from src.schemas.retry_request import RetryRequest
from src.schemas.retry_result import RetryResult
from src.value_objects import BackoffConfig, RetryConfig
from src.services.backoff_service import BackoffService
from src.services.event_service import EventService
from src.services.scheduler_service import SchedulerService


class RetryError(OpsboardError):
    """Base class for retry-related errors."""


class RetryExhaustedError(RetryError, InvalidStateError):
    """Raised when a job has already used all of its allowed attempts."""

    def __init__(self, scheduled_job_id: uuid.UUID, max_attempts: int) -> None:
        super().__init__(
            f"Retry attempts exhausted for job {scheduled_job_id} "
            f"(max_attempts={max_attempts})"
        )
        self.scheduled_job_id = scheduled_job_id
        self.max_attempts = max_attempts


class RetryPolicyNotFoundError(RetryError, NotFoundError):
    """Raised when a referenced retry policy does not exist."""

    def __init__(self, policy_id: uuid.UUID) -> None:
        super().__init__(f"Retry policy not found: {policy_id}")
        self.policy_id = policy_id


class RetryService:
    """Re-runs failed scheduled jobs under a bounded retry policy.

    Each retry runs synchronously through :class:`SchedulerService`, records a
    :class:`RetryAttempt` (with a backoff-derived ``next_retry_at``), and emits
    a domain event. Retries never exceed the configured ``max_attempts`` and
    use no recursion or threads.
    """

    def __init__(self, session: Session) -> None:
        self._session = session
        self._attempts = RetryAttemptRepository(session)
        self._policies = RetryPolicyRepository(session)
        self._scheduler = SchedulerService(session)
        self._backoff = BackoffService()
        self._events = EventService(session)

    def retry_job(
        self, scheduled_job_id: uuid.UUID, config: RetryConfig
    ) -> RetryAttempt:
        """Run one further attempt of a job, honoring ``config.max_attempts``.

        Raises :class:`RetryExhaustedError` if the job has already used all of
        its allowed attempts.
        """
        prior = self._attempts.get_by_job(scheduled_job_id)
        if len(prior) >= config.max_attempts:
            raise RetryExhaustedError(
                scheduled_job_id, config.max_attempts
            )

        attempt_number = len(prior) + 1

        # Reset a previously-failed job so the scheduler will run it again.
        job = self._scheduler.reset_for_retry(scheduled_job_id)
        self._scheduler.run_job(job.id)
        succeeded = job.status is ScheduledJobStatus.COMPLETED

        if succeeded:
            return self.record_attempt(
                scheduled_job_id,
                attempt_number,
                config,
                successful=True,
                error_message=None,
            )
        return self.record_attempt(
            scheduled_job_id,
            attempt_number,
            config,
            successful=False,
            error_message=job.error_message,
        )

    def record_attempt(
        self,
        scheduled_job_id: uuid.UUID,
        attempt_number: int,
        config: RetryConfig,
        *,
        successful: bool,
        error_message: str | None,
    ) -> RetryAttempt:
        """Persist a retry attempt and emit the matching domain event."""
        next_retry_at = None
        if not successful and attempt_number < config.max_attempts:
            backoff_config = BackoffConfig(
                strategy=config.strategy,
                base_delay_seconds=config.base_delay_seconds,
            )
            delay = self._backoff.calculate_delay_from_config(backoff_config, attempt_number)
            next_retry_at = utcnow() + timedelta(seconds=delay)

        attempt = self._attempts.add(
            RetryAttempt(
                scheduled_job_id=scheduled_job_id,
                attempt_number=attempt_number,
                error_message=error_message,
                next_retry_at=next_retry_at,
                successful=successful,
            )
        )

        event_type = (
            DomainEventType.RETRY_SUCCEEDED
            if successful
            else DomainEventType.RETRY_FAILED
        )
        self._events.record_event(
            event_type,
            {
                "scheduled_job_id": str(scheduled_job_id),
                "attempt_number": attempt_number,
            },
        )
        return attempt

    def get_attempts(
        self, scheduled_job_id: uuid.UUID
    ) -> list[RetryAttempt]:
        """Return all retry attempts for a scheduled job, oldest first."""
        return self._attempts.get_by_job(scheduled_job_id)

    def retry_job_with_policy(self, request: RetryRequest) -> RetryResult:
        """Retry a job using the named policy loaded from the database.

        1. Loads the :class:`RetryPolicy` by ``request.policy_id``.
        2. Raises :class:`RetryPolicyNotFoundError` if the policy is absent.
        3. Builds a :class:`RetryConfig` from the policy.
        4. Delegates to :meth:`retry_job` for the actual execution.
        5. Maps the resulting :class:`RetryAttempt` to a :class:`RetryResult`.
        """
        policy = self._policies.get(request.policy_id)
        if policy is None:
            raise RetryPolicyNotFoundError(request.policy_id)

        config = RetryConfig(
            strategy=policy.strategy,
            max_attempts=policy.max_attempts,
            base_delay_seconds=policy.base_delay_seconds,
        )

        attempt = self.retry_job(request.scheduled_job_id, config)

        prior_count = len(self._attempts.get_by_job(request.scheduled_job_id))
        exhausted = not attempt.successful and prior_count >= config.max_attempts

        return RetryResult(
            scheduled_job_id=request.scheduled_job_id,
            attempt_number=attempt.attempt_number,
            successful=attempt.successful,
            exhausted=exhausted,
            next_retry_at=attempt.next_retry_at,
            error_message=attempt.error_message,
        )
