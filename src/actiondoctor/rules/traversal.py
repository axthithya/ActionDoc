"""Shared typed traversal and location helpers for workflow rules."""

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from typing import Any, TypedDict

from actiondoctor.models import WorkflowFile, YamlLocation


@dataclass(frozen=True)
class JobContext:
    """A valid mapping-shaped job and its source context."""

    job_id: str
    job: Mapping[str, Any]

    @property
    def yaml_path(self) -> str:
        """YAML path to this job."""
        return f"jobs.{self.job_id}"


@dataclass(frozen=True)
class StepContext:
    """A mapping-shaped step belonging to a valid job."""

    job_id: str
    index: int
    step: Mapping[str, Any]

    @property
    def yaml_path(self) -> str:
        """YAML path to this step."""
        return f"jobs.{self.job_id}.steps[{self.index}]"


class LocationFields(TypedDict, total=False):
    """Optional source fields accepted by Finding."""

    line: int
    column: int


def iter_jobs(workflow: WorkflowFile) -> Iterator[JobContext]:
    """Yield string-keyed, mapping-shaped jobs."""
    jobs = workflow.parsed_content.get("jobs")
    if not isinstance(jobs, Mapping):
        return
    for job_id, job in jobs.items():
        if isinstance(job_id, str) and isinstance(job, Mapping):
            yield JobContext(job_id, job)


def iter_steps(job: JobContext) -> Iterator[StepContext]:
    """Yield mapping-shaped steps for one job."""
    steps = job.job.get("steps")
    if not isinstance(steps, list):
        return
    for index, step in enumerate(steps):
        if isinstance(step, Mapping):
            yield StepContext(job.job_id, index, step)


def location_fields(
    workflow: WorkflowFile,
    yaml_path: str,
    *,
    fallback_path: str | None = None,
) -> LocationFields:
    """Return the best captured source location for a finding."""
    location: YamlLocation | None = workflow.location_for(yaml_path)
    if location is None and fallback_path is not None:
        location = workflow.location_for(fallback_path)
    if location is None:
        return {}
    return {"line": location.line, "column": location.column}
