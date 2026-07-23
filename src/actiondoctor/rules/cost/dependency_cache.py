"""Shared implementation for setup-action dependency-cache rules."""

from pathlib import Path
from re import Pattern

from actiondoctor.models import Finding, RuleCategory, Severity, WorkflowFile
from actiondoctor.rules.cost.helpers import (
    action_matches,
    has_configured_option,
    iter_job_steps,
    iter_jobs,
    location_fields,
    shell_command,
)


class DependencyCacheRule:
    """Base implementation parameterized only by one ecosystem's constants."""

    rule_id: str
    title: str
    description: str
    setup_action: str
    install_pattern: Pattern[str]
    ecosystem: str
    category = RuleCategory.COST
    default_severity = Severity.LOW

    def evaluate(self, workflow: WorkflowFile) -> list[Finding]:
        """Report one finding per setup job with uncached dependency installs."""
        findings: list[Finding] = []
        for job in iter_jobs(workflow):
            steps = list(iter_job_steps(job))
            install_indices = [
                step.index
                for step in steps
                if (command := shell_command(step.step)) is not None
                and self.install_pattern.search(command) is not None
            ]
            if not install_indices:
                continue
            first_install = min(install_indices)
            setup_steps = [
                step for step in steps if action_matches(step.step, self.setup_action)
            ]
            if not setup_steps:
                continue
            if any(
                step.index < first_install and has_configured_option(step.step, "cache")
                for step in setup_steps
            ):
                continue
            if any(
                step.index < first_install
                and action_matches(step.step, "actions/cache")
                for step in steps
            ):
                continue

            install_step = next(step for step in steps if step.index == first_install)
            yaml_path = f"{install_step.yaml_path}.run"
            findings.append(
                Finding(
                    rule_id=self.rule_id,
                    title=self.title,
                    description=(
                        f"Job `{job.job_id}` installs {self.ecosystem} dependencies "
                        "without a dependency cache configured beforehand."
                    ),
                    severity=self.default_severity,
                    category=self.category,
                    file_path=Path(workflow.relative_path),
                    job_id=job.job_id,
                    yaml_path=yaml_path,
                    remediation=(
                        f"Configure the `{self.setup_action}` cache input or add a "
                        "suitable `actions/cache` step before dependency installation."
                    ),
                    **location_fields(workflow, yaml_path),
                )
            )
        return findings
