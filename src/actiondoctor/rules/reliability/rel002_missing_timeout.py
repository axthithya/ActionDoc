"""REL002: detect jobs without a positive static timeout."""

from pathlib import Path

from actiondoctor.models import Finding, RuleCategory, Severity, WorkflowFile
from actiondoctor.rules.reliability.helpers import (
    contains_expression,
    is_positive_timeout,
    iter_jobs,
    location_fields,
)


class MissingJobTimeoutRule:
    """Report ordinary jobs lacking a positive timeout."""

    rule_id = "REL002"
    title = "Missing Job Timeout"
    description = "A job has no positive timeout to bound its execution."
    category = RuleCategory.RELIABILITY
    default_severity = Severity.MEDIUM

    def evaluate(self, workflow: WorkflowFile) -> list[Finding]:
        findings: list[Finding] = []
        for job in iter_jobs(workflow):
            if "uses" in job.job:
                continue
            timeout = job.job.get("timeout-minutes")
            if is_positive_timeout(timeout):
                continue
            if isinstance(timeout, str) and contains_expression(timeout):
                continue
            yaml_path = f"{job.yaml_path}.timeout-minutes"
            findings.append(
                Finding(
                    rule_id=self.rule_id,
                    title=self.title,
                    description=f"Job `{job.job_id}` has no positive static timeout.",
                    severity=self.default_severity,
                    category=self.category,
                    file_path=Path(workflow.relative_path),
                    job_id=job.job_id,
                    yaml_path=yaml_path,
                    remediation=(
                        "Set `timeout-minutes` to an appropriate positive value based "
                        "on this job's expected duration."
                    ),
                    **location_fields(
                        workflow,
                        yaml_path,
                        fallback_path=job.yaml_path,
                    ),
                )
            )
        return findings
