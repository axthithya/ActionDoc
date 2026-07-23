"""MAINT003: detect run steps without descriptive names."""

from pathlib import Path

from actiondoctor.models import Finding, RuleCategory, Severity, WorkflowFile
from actiondoctor.rules.maintainability.helpers import normalized_non_empty_string
from actiondoctor.rules.traversal import iter_jobs, iter_steps, location_fields


class UnnamedRunStepRule:
    """Report scalar run steps without non-empty names."""

    rule_id = "MAINT003"
    title = "Unnamed Run Step"
    description = "A run step should define a descriptive non-empty name."
    category = RuleCategory.MAINTAINABILITY
    default_severity = Severity.LOW

    def evaluate(self, workflow: WorkflowFile) -> list[Finding]:
        findings: list[Finding] = []
        for job in iter_jobs(workflow):
            for step in iter_steps(job):
                if not isinstance(step.step.get("run"), str):
                    continue
                if normalized_non_empty_string(step.step.get("name")) is not None:
                    continue
                yaml_path = f"{step.yaml_path}.name"
                findings.append(
                    Finding(
                        rule_id=self.rule_id,
                        title=self.title,
                        description=(
                            f"Run step at index {step.index} in job `{job.job_id}` "
                            "has no descriptive non-empty name."
                        ),
                        severity=self.default_severity,
                        category=self.category,
                        file_path=Path(workflow.relative_path),
                        job_id=job.job_id,
                        yaml_path=yaml_path,
                        remediation=(
                            "Add a concise `name` describing what the step runs."
                        ),
                        **location_fields(
                            workflow,
                            yaml_path,
                            fallback_path=f"{step.yaml_path}.run",
                        ),
                    )
                )
        return findings
