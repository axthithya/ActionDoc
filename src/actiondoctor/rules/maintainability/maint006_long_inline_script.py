"""MAINT006: detect run steps with long inline shell scripts."""

from pathlib import Path

from actiondoctor.models import Finding, RuleCategory, Severity, WorkflowFile
from actiondoctor.rules.maintainability.helpers import (
    non_empty_script_line_count,
    normalized_non_empty_string,
)
from actiondoctor.rules.traversal import iter_jobs, iter_steps, location_fields

MAX_INLINE_SCRIPT_LINES = 20


class LongInlineShellScriptRule:
    """Report run scripts containing more than 20 non-empty lines."""

    rule_id = "MAINT006"
    title = "Long Inline Shell Script"
    description = "A run step contains more than 20 non-empty script lines."
    category = RuleCategory.MAINTAINABILITY
    default_severity = Severity.LOW

    def evaluate(self, workflow: WorkflowFile) -> list[Finding]:
        findings: list[Finding] = []
        for job in iter_jobs(workflow):
            for step in iter_steps(job):
                line_count = non_empty_script_line_count(step.step.get("run"))
                if line_count is None or line_count <= MAX_INLINE_SCRIPT_LINES:
                    continue
                yaml_path = f"{step.yaml_path}.run"
                step_name = normalized_non_empty_string(step.step.get("name"))
                label = (
                    f"step `{step_name}` at index {step.index}"
                    if step_name is not None
                    else f"step at index {step.index}"
                )
                findings.append(
                    Finding(
                        rule_id=self.rule_id,
                        title=self.title,
                        description=(
                            f"Job `{job.job_id}` {label} contains {line_count} "
                            f"non-empty script lines, above the "
                            f"{MAX_INLINE_SCRIPT_LINES}-line threshold."
                        ),
                        severity=self.default_severity,
                        category=self.category,
                        file_path=Path(workflow.relative_path),
                        job_id=job.job_id,
                        yaml_path=yaml_path,
                        remediation=(
                            "Consider moving the shell logic into a version-controlled "
                            "script to improve testing, readability, and reuse."
                        ),
                        **location_fields(workflow, yaml_path),
                    )
                )
        return findings
