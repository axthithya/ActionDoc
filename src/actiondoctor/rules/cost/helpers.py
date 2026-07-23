"""Focused traversal and static-analysis helpers for cost rules."""

import re
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from typing import Any, TypedDict

from actiondoctor.models import WorkflowFile, YamlLocation

_COMMAND_BOUNDARY = r"(?:^|[\n;&|])\s*"
PYTHON_INSTALL = re.compile(
    _COMMAND_BOUNDARY + r"(?:pip(?:3)?\s+install\b|python(?:3)?\s+-m\s+pip\s+install\b|"
    r"poetry\s+install\b|pipenv\s+install\b)",
    re.IGNORECASE,
)
NODE_INSTALL = re.compile(
    _COMMAND_BOUNDARY + r"(?:npm\s+(?:ci|install)\b|yarn\s+install\b|pnpm\s+install\b)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class JobContext:
    """A mapping-shaped job and its source context."""

    job_id: str
    job: Mapping[str, Any]

    @property
    def yaml_path(self) -> str:
        """YAML path to this job."""
        return f"jobs.{self.job_id}"


@dataclass(frozen=True)
class JobStep:
    """A mapping-shaped step belonging to one job."""

    job_id: str
    index: int
    step: Mapping[str, Any]

    @property
    def yaml_path(self) -> str:
        """YAML path to this step."""
        return f"jobs.{self.job_id}.steps[{self.index}]"


@dataclass(frozen=True)
class MatrixSize:
    """Statically countable base matrix size and explicit include additions."""

    base_combinations: int
    include_additions: int | None


class LocationFields(TypedDict, total=False):
    """Optional source fields accepted by Finding."""

    line: int
    column: int


def iter_jobs(workflow: WorkflowFile) -> Iterator[JobContext]:
    """Yield only string-keyed, mapping-shaped jobs."""
    jobs = workflow.parsed_content.get("jobs")
    if not isinstance(jobs, Mapping):
        return
    for job_id, job in jobs.items():
        if isinstance(job_id, str) and isinstance(job, Mapping):
            yield JobContext(job_id=job_id, job=job)


def iter_job_steps(context: JobContext) -> Iterator[JobStep]:
    """Yield mapping-shaped steps from one job."""
    steps = context.job.get("steps")
    if not isinstance(steps, list):
        return
    for index, step in enumerate(steps):
        if isinstance(step, Mapping):
            yield JobStep(context.job_id, index, step)


def action_matches(step: Mapping[str, Any], action_name: str) -> bool:
    """Match an action owner/name independently of its revision and case."""
    uses = step.get("uses")
    if not isinstance(uses, str):
        return False
    name = uses.strip().split("@", maxsplit=1)[0]
    return name.casefold() == action_name.casefold()


def has_configured_option(step: Mapping[str, Any], option: str) -> bool:
    """Return whether an action input has a nonempty configured value."""
    inputs = step.get("with")
    if not isinstance(inputs, Mapping) or option not in inputs:
        return False
    value = inputs[option]
    return value is not None and value is not False and value != ""


def shell_command(step: Mapping[str, Any]) -> str | None:
    """Return normalized line endings for a scalar run command."""
    command = step.get("run")
    if not isinstance(command, str):
        return None
    return command.replace("\r\n", "\n").replace("\r", "\n")


def location_fields(workflow: WorkflowFile, yaml_path: str) -> LocationFields:
    """Return optional finding location fields for a YAML path."""
    location: YamlLocation | None = workflow.location_for(yaml_path)
    if location is None:
        return {}
    return {"line": location.line, "column": location.column}


def has_enabled_trigger(workflow: WorkflowFile, event_name: str) -> bool:
    """Recognize an event while treating an explicit false value as disabled."""
    triggers = workflow.parsed_content.get("on")
    if isinstance(triggers, str):
        return triggers == event_name
    if isinstance(triggers, list):
        return event_name in triggers
    if isinstance(triggers, Mapping):
        return event_name in triggers and triggers[event_name] is not False
    return False


def static_matrix_size(matrix: Any) -> MatrixSize | None:
    """Count a fully static matrix base product without evaluating expressions."""
    if not isinstance(matrix, Mapping):
        return None

    dimensions: list[list[Any]] = []
    for key, values in matrix.items():
        if key in {"include", "exclude"}:
            continue
        if (
            not isinstance(key, str)
            or not isinstance(values, list)
            or _contains_expression(values)
        ):
            return None
        dimensions.append(values)
    if not dimensions:
        return None

    product = 1
    for values in dimensions:
        product *= len(values)

    include = matrix.get("include")
    include_additions = len(include) if isinstance(include, list) else None
    return MatrixSize(product, include_additions)


def _contains_expression(value: Any) -> bool:
    """Return whether a matrix dimension contains a dynamic expression."""
    if isinstance(value, str):
        return "${{" in value
    if isinstance(value, Mapping):
        return any(
            _contains_expression(key) or _contains_expression(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(_contains_expression(item) for item in value)
    return False
