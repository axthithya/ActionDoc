"""MAINT004: detect jobs with more than the supported step threshold."""

from pathlib import Path

from actiondoctor.models import Finding, RuleCategory, Severity, WorkflowFile
from actiondoctor.rules.maintainability.helpers import valid_steps
from actiondoctor.rules.traversal import iter_jobs, location_fields

MAX_JOB_STEPS = 15


class OversizedJobRule:
    """Report jobs containing more than 15 mapping-shaped steps."""

    rule_id = "MAINT004"
    title = "Oversized Job"
    description = "A job contains more than 15 valid steps."
    category = RuleCategory.MAINTAINABILITY
    default_severity = Severity.MEDIUM

    def evaluate(self, workflow: WorkflowFile) -> list[Finding]:
        findings: list[Finding] = []
        for job in iter_jobs(workflow):
            step_count = len(valid_steps(job))
            if step_count <= MAX_JOB_STEPS:
                continue
            yaml_path = f"{job.yaml_path}.steps"
            findings.append(
                Finding(
                    rule_id=self.rule_id,
                    title=self.title,
                    description=(
                        f"Job `{job.job_id}` contains {step_count} valid steps, "
                        f"above the {MAX_JOB_STEPS}-step threshold."
                    ),
                    severity=self.default_severity,
                    category=self.category,
                    file_path=Path(workflow.relative_path),
                    job_id=job.job_id,
                    yaml_path=yaml_path,
                    remediation=(
                        "Consider whether focused jobs, a reusable workflow, a "
                        "composite action, or a version-controlled script would make "
                        "this job easier to maintain."
                    ),
                    **location_fields(workflow, yaml_path),
                )
            )
        return findings
