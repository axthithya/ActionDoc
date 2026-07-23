"""REL001: require a non-empty top-level jobs mapping."""

from collections.abc import Mapping
from pathlib import Path

from actiondoctor.models import Finding, RuleCategory, Severity, WorkflowFile


class MissingJobsRule:
    """Report workflows without at least one job."""

    rule_id = "REL001"
    title = "Missing Jobs"
    description = "The workflow should define a non-empty top-level jobs mapping."
    category = RuleCategory.RELIABILITY
    default_severity = Severity.HIGH

    def evaluate(self, workflow: WorkflowFile) -> list[Finding]:
        """Return one finding when `jobs` is absent, invalid, or empty."""
        jobs = workflow.parsed_content.get("jobs")
        if isinstance(jobs, Mapping) and jobs:
            return []

        return [
            Finding(
                rule_id=self.rule_id,
                title=self.title,
                description=self.description,
                severity=self.default_severity,
                category=self.category,
                file_path=Path(workflow.relative_path),
                yaml_path="jobs",
                remediation="Add at least one job under the top-level `jobs` key.",
            )
        ]
