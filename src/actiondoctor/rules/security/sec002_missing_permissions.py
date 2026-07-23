"""SEC002: require explicit workflow or per-job permissions."""

from collections.abc import Mapping
from pathlib import Path

from actiondoctor.models import Finding, RuleCategory, Severity, WorkflowFile


class MissingExplicitPermissionsRule:
    """Report workflows whose jobs may inherit repository permission defaults."""

    rule_id = "SEC002"
    title = "Missing Explicit Permissions"
    description = "The workflow does not explicitly define permissions for every job."
    category = RuleCategory.SECURITY
    default_severity = Severity.MEDIUM

    def evaluate(self, workflow: WorkflowFile) -> list[Finding]:
        """Return one workflow-level finding when defaults may be inherited."""
        content = workflow.parsed_content
        if "permissions" in content:
            return []

        jobs = content.get("jobs")
        if (
            isinstance(jobs, Mapping)
            and jobs
            and all(
                isinstance(job, Mapping) and "permissions" in job
                for job in jobs.values()
            )
        ):
            return []

        return [
            Finding(
                rule_id=self.rule_id,
                title=self.title,
                description=(
                    "One or more jobs rely on undeclared token permission defaults."
                ),
                severity=self.default_severity,
                category=self.category,
                file_path=Path(workflow.relative_path),
                yaml_path="permissions",
                remediation=(
                    "Declare least-privilege `permissions` at workflow level or "
                    "explicitly for every job."
                ),
            )
        ]
