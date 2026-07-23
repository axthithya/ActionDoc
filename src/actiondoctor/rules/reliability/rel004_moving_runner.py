"""REL004: detect moving GitHub-hosted runner labels."""

from pathlib import Path

from actiondoctor.models import Finding, RuleCategory, Severity, WorkflowFile
from actiondoctor.rules.reliability.helpers import (
    iter_jobs,
    location_fields,
    moving_runner_labels,
)


class MovingRunnerLabelRule:
    """Report static `*-latest` GitHub-hosted runner labels."""

    rule_id = "REL004"
    title = "Moving Runner Label"
    description = "A moving runner label may resolve to a newer image over time."
    category = RuleCategory.RELIABILITY
    default_severity = Severity.LOW

    def evaluate(self, workflow: WorkflowFile) -> list[Finding]:
        findings: list[Finding] = []
        for job in iter_jobs(workflow):
            labels = moving_runner_labels(job.job.get("runs-on"))
            if not labels:
                continue
            yaml_path = f"{job.yaml_path}.runs-on"
            rendered_labels = ", ".join(f"`{label}`" for label in labels)
            findings.append(
                Finding(
                    rule_id=self.rule_id,
                    title=self.title,
                    description=(
                        f"Job `{job.job_id}` uses moving runner label(s) "
                        f"{rendered_labels}, which may point to newer images later."
                    ),
                    severity=self.default_severity,
                    category=self.category,
                    file_path=Path(workflow.relative_path),
                    job_id=job.job_id,
                    yaml_path=yaml_path,
                    remediation=(
                        "Use a versioned runner label when reproducible operating "
                        "system behavior is important."
                    ),
                    **location_fields(workflow, yaml_path),
                )
            )
        return findings
