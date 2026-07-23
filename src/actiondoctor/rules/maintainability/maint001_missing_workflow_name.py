"""MAINT001: require a non-empty top-level workflow name."""

from pathlib import Path

from actiondoctor.models import Finding, RuleCategory, Severity, WorkflowFile


class MissingWorkflowNameRule:
    """Report workflows without a useful top-level name."""

    rule_id = "MAINT001"
    title = "Missing Workflow Name"
    description = "The workflow should define a non-empty top-level name."
    category = RuleCategory.MAINTAINABILITY
    default_severity = Severity.LOW

    def evaluate(self, workflow: WorkflowFile) -> list[Finding]:
        """Return one finding when `name` is absent, null, or blank."""
        name = workflow.parsed_content.get("name")
        if name is not None and (not isinstance(name, str) or bool(name.strip())):
            return []

        return [
            Finding(
                rule_id=self.rule_id,
                title=self.title,
                description=self.description,
                severity=self.default_severity,
                category=self.category,
                file_path=Path(workflow.relative_path),
                yaml_path="name",
                remediation="Add a descriptive top-level `name` to the workflow.",
            )
        ]
