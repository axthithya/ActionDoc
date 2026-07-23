"""Focused traversal and static inspection helpers for reliability rules."""

import re
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from typing import Any, TypedDict

from actiondoctor.models import WorkflowFile, YamlLocation

MOVING_RUNNER_LABELS = frozenset({"ubuntu-latest", "windows-latest", "macos-latest"})
FLOATING_IMAGE_TAGS = frozenset(
    {"latest", "edge", "nightly", "stable", "canary", "dev", "main", "master"}
)
_DIGEST_REFERENCE = re.compile(
    r"@[A-Za-z0-9_+.-]+:[A-Za-z0-9=_+.-]+$",
)
_HEALTH_COMMAND = re.compile(r"(?:^|\s)--health-cmd(?:=|\s|$)")


@dataclass(frozen=True)
class JobContext:
    """A valid mapping-shaped job and its source context."""

    job_id: str
    job: Mapping[str, Any]

    @property
    def yaml_path(self) -> str:
        return f"jobs.{self.job_id}"


@dataclass(frozen=True)
class StepContext:
    """A mapping-shaped step belonging to a valid job."""

    job_id: str
    index: int
    step: Mapping[str, Any]

    @property
    def yaml_path(self) -> str:
        return f"jobs.{self.job_id}.steps[{self.index}]"


@dataclass(frozen=True)
class ServiceContext:
    """A statically analyzable service container definition."""

    job_id: str
    service_id: str
    service: Mapping[str, Any]
    image: str

    @property
    def yaml_path(self) -> str:
        return f"jobs.{self.job_id}.services.{self.service_id}"


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


def iter_services(job: JobContext) -> Iterator[ServiceContext]:
    """Yield services with static scalar image references."""
    services = job.job.get("services")
    if not isinstance(services, Mapping):
        return
    for service_id, service in services.items():
        if not isinstance(service_id, str) or not isinstance(service, Mapping):
            continue
        image = service.get("image")
        if (
            not isinstance(image, str)
            or not image.strip()
            or contains_expression(image)
        ):
            continue
        yield ServiceContext(job.job_id, service_id, service, image.strip())


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


def is_literal_true(value: Any) -> bool:
    """Recognize only YAML's literal boolean true."""
    return value is True


def is_positive_timeout(value: Any) -> bool:
    """Recognize a positive static timeout while excluding booleans."""
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0


def contains_expression(value: str) -> bool:
    """Recognize an unevaluated GitHub expression."""
    return "${{" in value


def is_mutable_image_reference(image: str) -> bool | None:
    """Classify a static image reference; return None when analysis is unsafe."""
    reference = image.strip()
    if not reference or contains_expression(reference):
        return None
    if _DIGEST_REFERENCE.search(reference) is not None:
        return False

    final_component = reference.rsplit("/", maxsplit=1)[-1]
    if ":" not in final_component:
        return True
    tag = final_component.rsplit(":", maxsplit=1)[1].casefold()
    if not tag:
        return None
    return tag in FLOATING_IMAGE_TAGS


def moving_runner_labels(value: Any) -> tuple[str, ...]:
    """Return moving labels only from a fully static scalar or label list."""
    if isinstance(value, str):
        if contains_expression(value):
            return ()
        return (value,) if value in MOVING_RUNNER_LABELS else ()
    if not isinstance(value, list):
        return ()
    if not all(
        isinstance(label, str) and not contains_expression(label) for label in value
    ):
        return ()
    return tuple(
        label
        for label in value
        if isinstance(label, str) and label in MOVING_RUNNER_LABELS
    )


def has_health_check(options: Any) -> bool | None:
    """Classify static Docker options; return None for unsupported/dynamic values."""
    if options is None:
        return False
    if not isinstance(options, str) or contains_expression(options):
        return None
    return _HEALTH_COMMAND.search(options) is not None
