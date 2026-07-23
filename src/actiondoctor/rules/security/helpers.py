"""Defensive traversal helpers shared by security rules."""

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from typing import Any, TypedDict

from actiondoctor.models import WorkflowFile, YamlLocation


@dataclass(frozen=True)
class StepContext:
    """A valid mapping-shaped workflow step and its source context."""

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


def iter_steps(workflow: WorkflowFile) -> Iterator[StepContext]:
    """Yield mapping-shaped steps from mapping-shaped jobs."""
    jobs = workflow.parsed_content.get("jobs")
    if not isinstance(jobs, Mapping):
        return
    for job_id, job in jobs.items():
        if not isinstance(job_id, str) or not isinstance(job, Mapping):
            continue
        steps = job.get("steps")
        if not isinstance(steps, list):
            continue
        for index, step in enumerate(steps):
            if isinstance(step, Mapping):
                yield StepContext(job_id=job_id, index=index, step=step)


def location_fields(
    workflow: WorkflowFile,
    yaml_path: str,
) -> LocationFields:
    """Return optional finding location fields for a YAML path."""
    location: YamlLocation | None = workflow.location_for(yaml_path)
    if location is None:
        return {}
    return {"line": location.line, "column": location.column}


def has_trigger(workflow: WorkflowFile, event_name: str) -> bool:
    """Return whether the workflow declares a specific trigger."""
    triggers = workflow.parsed_content.get("on")
    if isinstance(triggers, str):
        return triggers == event_name
    if isinstance(triggers, list):
        return event_name in triggers
    if isinstance(triggers, Mapping):
        return event_name in triggers
    return False
