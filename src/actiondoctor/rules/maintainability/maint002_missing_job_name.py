"""MAINT002: detect ordinary jobs without descriptive names."""

from pathlib import Path

from actiondoctor.models import Finding, RuleCategory, Severity, WorkflowFile
from actiondoctor.rules.maintainability.helpers import normalized_non_empty_string
from actiondoctor.rules.traversal import iter_jobs, location_fields


class MissingJobNameRule:
    """Report mapping-shaped non-reusable jobs without non-empty names."""

    rule_id = "MAINT002"
    title = "Missing Job Name"
    description = "A job should define a descriptive non-empty name."
    category = RuleCategory.MAINTAINABILITY
    default_severity = Severity.LOW

    def evaluate(self, workflow: WorkflowFile) -> list[Finding]:
        findings: list[Finding] = []
        for job in iter_jobs(workflow):
            if "uses" in job.job:
                continue
            if normalized_non_empty_string(job.job.get("name")) is not None:
                continue
            yaml_path = f"{job.yaml_path}.name"
            findings.append(
                Finding(
                    rule_id=self.rule_id,
                    title=self.title,
                    description=(
                        f"Job `{job.job_id}` has no descriptive non-empty name."
                    ),
                    severity=self.default_severity,
                    category=self.category,
                    file_path=Path(workflow.relative_path),
                    job_id=job.job_id,
                    yaml_path=yaml_path,
                    remediation=(
                        "Add a descriptive job `name` so workflow runs are easier "
                        "to understand in the GitHub Actions interface."
                    ),
                    **location_fields(
                        workflow,
                        yaml_path,
                        fallback_path=job.yaml_path,
                    ),
                )
            )
        return findings
