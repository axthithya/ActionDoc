"""COST001: detect pull-request workflows without cancellation protection."""

from collections.abc import Mapping
from pathlib import Path

from actiondoctor.models import Finding, RuleCategory, Severity, WorkflowFile
from actiondoctor.rules.cost.helpers import has_enabled_trigger, location_fields


class MissingConcurrencyCancellationRule:
    """Report PR-triggered workflows not statically protected by cancellation."""

    rule_id = "COST001"
    title = "Missing Concurrency Cancellation"
    description = "A pull-request workflow does not cancel superseded runs."
    category = RuleCategory.COST
    default_severity = Severity.MEDIUM

    def evaluate(self, workflow: WorkflowFile) -> list[Finding]:
        """Require a literal true top-level cancel-in-progress value."""
        if not (
            has_enabled_trigger(workflow, "pull_request")
            or has_enabled_trigger(workflow, "pull_request_target")
        ):
            return []

        concurrency = workflow.parsed_content.get("concurrency")
        if (
            isinstance(concurrency, Mapping)
            and concurrency.get("cancel-in-progress") is True
        ):
            return []

        cancel_value = (
            concurrency.get("cancel-in-progress")
            if isinstance(concurrency, Mapping)
            else None
        )
        uncertain = isinstance(cancel_value, str) and "${{" in cancel_value
        detail = (
            "Concurrency cancellation is expression-based and cannot be confirmed "
            "statically."
            if uncertain
            else "The pull-request workflow does not set `cancel-in-progress: true`."
        )
        yaml_path = (
            "concurrency.cancel-in-progress"
            if isinstance(concurrency, Mapping) and "cancel-in-progress" in concurrency
            else "concurrency"
        )
        return [
            Finding(
                rule_id=self.rule_id,
                title=self.title,
                description=detail,
                severity=self.default_severity,
                category=self.category,
                file_path=Path(workflow.relative_path),
                yaml_path=yaml_path,
                remediation=(
                    "Configure top-level concurrency with a group based on the "
                    "workflow and branch or pull request, and set "
                    "`cancel-in-progress: true`."
                ),
                **location_fields(workflow, yaml_path),
            )
        ]
