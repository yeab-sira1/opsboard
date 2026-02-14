"""Backoff configuration value object."""

from __future__ import annotations

from src.models.retry_policy import RetryStrategy


class BackoffConfig:
    """Immutable configuration for a backoff strategy."""

    def __init__(
        self, strategy: RetryStrategy, base_delay_seconds: int
    ) -> None:
        if base_delay_seconds < 0:
            raise ValueError(
                f"base_delay_seconds must be >= 0, got {base_delay_seconds}"
            )
        self._strategy = strategy
        self._base_delay_seconds = base_delay_seconds

    @property
    def strategy(self) -> RetryStrategy:
        """The backoff strategy."""
        return self._strategy

    @property
    def base_delay_seconds(self) -> int:
        """The base delay in seconds."""
        return self._base_delay_seconds

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, BackoffConfig):
            return NotImplemented
        return (
            self._strategy == other._strategy
            and self._base_delay_seconds == other._base_delay_seconds
        )

    def __repr__(self) -> str:
        return (
            f"BackoffConfig(strategy={self._strategy.name}, "
            f"base_delay_seconds={self._base_delay_seconds})"
        )
