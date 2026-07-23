"""REL003: detect mutable job and service container image references."""

from collections.abc import Mapping
from pathlib import Path

from actiondoctor.models import Finding, RuleCategory, Severity, WorkflowFile
from actiondoctor.rules.reliability.helpers import (
    is_mutable_image_reference,
    iter_jobs,
    iter_services,
    location_fields,
)


class MutableContainerImageRule:
    """Report untagged and confidently floating container image references."""

    rule_id = "REL003"
    title = "Mutable Container Image Reference"
    description = "A container image reference can resolve to changing content."
    category = RuleCategory.RELIABILITY
    default_severity = Severity.MEDIUM

    def evaluate(self, workflow: WorkflowFile) -> list[Finding]:
        findings: list[Finding] = []
        for job in iter_jobs(workflow):
            container = job.job.get("container")
            if isinstance(container, Mapping):
                image = container.get("image")
                if isinstance(image, str):
                    finding = self._finding(
                        workflow,
                        job.job_id,
                        image,
                        f"{job.yaml_path}.container.image",
                        "job container",
                    )
                    if finding is not None:
                        findings.append(finding)
            for service in iter_services(job):
                finding = self._finding(
                    workflow,
                    job.job_id,
                    service.image,
                    f"{service.yaml_path}.image",
                    f"service `{service.service_id}`",
                )
                if finding is not None:
                    findings.append(finding)
        return findings

    def _finding(
        self,
        workflow: WorkflowFile,
        job_id: str,
        image: str,
        yaml_path: str,
        target: str,
    ) -> Finding | None:
        if is_mutable_image_reference(image) is not True:
            return None
        return Finding(
            rule_id=self.rule_id,
            title=self.title,
            description=(
                f"Job `{job_id}` {target} uses mutable image reference `{image}`."
            ),
            severity=self.default_severity,
            category=self.category,
            file_path=Path(workflow.relative_path),
            job_id=job_id,
            yaml_path=yaml_path,
            remediation=(
                "Pin the image to a fixed version tag or, for stronger "
                "reproducibility, an immutable digest."
            ),
            **location_fields(workflow, yaml_path),
        )
