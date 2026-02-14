"""Retry configuration value object."""

from __future__ import annotations

from src.models.retry_policy import RetryStrategy


class RetryConfig:
    """Immutable configuration describing how a job should be retried."""

    def __init__(
        self,
        strategy: RetryStrategy,
        max_attempts: int,
        base_delay_seconds: int,
    ) -> None:
        if max_attempts < 1:
            raise ValueError(
                f"max_attempts must be >= 1, got {max_attempts}"
            )
        if base_delay_seconds < 0:
            raise ValueError(
                f"base_delay_seconds must be >= 0, got {base_delay_seconds}"
            )
        self._strategy = strategy
        self._max_attempts = max_attempts
        self._base_delay_seconds = base_delay_seconds

    @property
    def strategy(self) -> RetryStrategy:
        """The retry strategy."""
        return self._strategy

    @property
    def max_attempts(self) -> int:
        """The maximum number of attempts allowed."""
        return self._max_attempts

    @property
    def base_delay_seconds(self) -> int:
        """The base delay in seconds."""
        return self._base_delay_seconds

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, RetryConfig):
            return NotImplemented
        return (
            self._strategy == other._strategy
            and self._max_attempts == other._max_attempts
            and self._base_delay_seconds == other._base_delay_seconds
        )

    def __repr__(self) -> str:
        return (
            f"RetryConfig(strategy={self._strategy.name}, "
            f"max_attempts={self._max_attempts}, "
            f"base_delay_seconds={self._base_delay_seconds})"
        )
