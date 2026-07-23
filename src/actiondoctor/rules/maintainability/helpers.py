"""Focused normalization and counting helpers for maintainability rules."""

from typing import Any

from actiondoctor.rules.traversal import JobContext, StepContext, iter_steps


def normalized_non_empty_string(value: Any) -> str | None:
    """Trim a string and return None when it is absent or empty."""
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def normalized_step_name(value: Any) -> str | None:
    """Normalize a non-empty step name for case-insensitive comparison."""
    normalized = normalized_non_empty_string(value)
    return normalized.casefold() if normalized is not None else None


def valid_steps(job: JobContext) -> tuple[StepContext, ...]:
    """Return only mapping-shaped steps from one job."""
    return tuple(iter_steps(job))


def non_empty_script_line_count(value: Any) -> int | None:
    """Count non-empty lines in a scalar run script."""
    if not isinstance(value, str):
        return None
    return sum(bool(line.strip()) for line in value.splitlines())
