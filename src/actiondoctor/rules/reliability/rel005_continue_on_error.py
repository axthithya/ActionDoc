"""REL005: detect literal continue-on-error settings."""

from pathlib import Path

from actiondoctor.models import Finding, RuleCategory, Severity, WorkflowFile
from actiondoctor.rules.reliability.helpers import (
    is_literal_true,
    iter_jobs,
    iter_steps,
    location_fields,
)


class ContinueOnErrorRule:
    """Report job- and step-level failures explicitly configured to be ignored."""

    rule_id = "REL005"
    title = "Failure Ignored With Continue-on-Error"
    description = "A literal continue-on-error setting allows failure to be ignored."
    category = RuleCategory.RELIABILITY
    default_severity = Severity.MEDIUM

    def evaluate(self, workflow: WorkflowFile) -> list[Finding]:
        findings: list[Finding] = []
        for job in iter_jobs(workflow):
            if is_literal_true(job.job.get("continue-on-error")):
                yaml_path = f"{job.yaml_path}.continue-on-error"
                findings.append(
                    self._finding(
                        workflow,
                        job.job_id,
                        yaml_path,
                        Severity.HIGH,
                        (
                            f"Job `{job.job_id}` is allowed to fail without failing "
                            "the run, which may let later jobs or deployments continue."
                        ),
                    )
                )
            for step in iter_steps(job):
                if not is_literal_true(step.step.get("continue-on-error")):
                    continue
                yaml_path = f"{step.yaml_path}.continue-on-error"
                name = step.step.get("name")
                step_label = (
                    f"step `{name}` at index {step.index}"
                    if isinstance(name, str) and name.strip()
                    else f"step at index {step.index}"
                )
                findings.append(
                    self._finding(
                        workflow,
                        job.job_id,
                        yaml_path,
                        Severity.MEDIUM,
                        (
                            f"Job `{job.job_id}` {step_label} is allowed to fail, "
                            "which may let later jobs or deployments continue."
                        ),
                    )
                )
        return findings

    def _finding(
        self,
        workflow: WorkflowFile,
        job_id: str,
        yaml_path: str,
        severity: Severity,
        description: str,
    ) -> Finding:
        return Finding(
            rule_id=self.rule_id,
            title=self.title,
            description=description,
            severity=severity,
            category=self.category,
            file_path=Path(workflow.relative_path),
            job_id=job_id,
            yaml_path=yaml_path,
            remediation=(
                "Confirm that ignoring this failure is intentional and ensure the "
                "failure remains visible to maintainers."
            ),
            **location_fields(workflow, yaml_path),
        )
