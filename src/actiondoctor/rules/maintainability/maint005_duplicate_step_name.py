"""MAINT005: detect duplicate normalized step names within a job."""

from pathlib import Path

from actiondoctor.models import Finding, RuleCategory, Severity, WorkflowFile
from actiondoctor.rules.maintainability.helpers import (
    normalized_non_empty_string,
    normalized_step_name,
)
from actiondoctor.rules.traversal import iter_jobs, iter_steps, location_fields


class DuplicateStepNameRule:
    """Report every duplicate non-empty step name after its first occurrence."""

    rule_id = "MAINT005"
    title = "Duplicate Step Name"
    description = "A job contains duplicate normalized step names."
    category = RuleCategory.MAINTAINABILITY
    default_severity = Severity.LOW

    def evaluate(self, workflow: WorkflowFile) -> list[Finding]:
        findings: list[Finding] = []
        for job in iter_jobs(workflow):
            seen: set[str] = set()
            for step in iter_steps(job):
                comparable_name = normalized_step_name(step.step.get("name"))
                if comparable_name is None:
                    continue
                if comparable_name not in seen:
                    seen.add(comparable_name)
                    continue
                display_name = normalized_non_empty_string(step.step.get("name"))
                assert display_name is not None
                yaml_path = f"{step.yaml_path}.name"
                findings.append(
                    Finding(
                        rule_id=self.rule_id,
                        title=self.title,
                        description=(
                            f"Step name `{display_name}` duplicates an earlier step "
                            f"name in job `{job.job_id}`."
                        ),
                        severity=self.default_severity,
                        category=self.category,
                        file_path=Path(workflow.relative_path),
                        job_id=job.job_id,
                        yaml_path=yaml_path,
                        remediation=(
                            "Give this step a distinct name that describes its role."
                        ),
                        **location_fields(workflow, yaml_path),
                    )
                )
        return findings
