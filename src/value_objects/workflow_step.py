"""Workflow step value object."""

from __future__ import annotations


class WorkflowStep:
    """An immutable record of one step within a workflow run."""

    def __init__(
        self, step_name: str, successful: bool, message: str = ""
    ) -> None:
        if not step_name:
            raise ValueError("step_name must not be empty")
        self._step_name = step_name
        self._successful = successful
        self._message = message

    @property
    def step_name(self) -> str:
        """The name of the step."""
        return self._step_name

    @property
    def successful(self) -> bool:
        """Whether the step completed successfully."""
        return self._successful

    @property
    def message(self) -> str:
        """A human-readable description of the step outcome."""
        return self._message

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, WorkflowStep):
            return NotImplemented
        return (
            self._step_name == other._step_name
            and self._successful == other._successful
            and self._message == other._message
        )

    def __repr__(self) -> str:
        return (
            f"WorkflowStep(step_name={self._step_name!r}, "
            f"successful={self._successful!r}, message={self._message!r})"
        )
