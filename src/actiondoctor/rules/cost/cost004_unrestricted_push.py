"""COST004: detect push workflows without branch, path, or tag filters."""

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from actiondoctor.models import Finding, RuleCategory, Severity, WorkflowFile
from actiondoctor.rules.cost.helpers import location_fields

PUSH_FILTERS = {
    "branches",
    "branches-ignore",
    "paths",
    "paths-ignore",
    "tags",
    "tags-ignore",
}
_ABSENT = object()


class UnrestrictedPushRule:
    """Report statically identifiable push triggers that run without filters."""

    rule_id = "COST004"
    title = "Unrestricted Push Workflow"
    description = "A push trigger has no branch, path, or tag filters."
    category = RuleCategory.COST
    default_severity = Severity.LOW

    def evaluate(self, workflow: WorkflowFile) -> list[Finding]:
        """Ignore absent, disabled, filtered, dynamic, or ambiguous push triggers."""
        push = self._push_configuration(workflow.parsed_content.get("on"))
        if push is _ABSENT or push is False:
            return []
        if isinstance(push, Mapping):
            if any(key in push for key in PUSH_FILTERS):
                return []
        elif push is not None and push is not True:
            return []

        yaml_path = "on.push"
        return [
            Finding(
                rule_id=self.rule_id,
                title=self.title,
                description=(
                    "The workflow's push trigger has no branch, path, or tag filters; "
                    "filters may reduce unnecessary runs when appropriate."
                ),
                severity=self.default_severity,
                category=self.category,
                file_path=Path(workflow.relative_path),
                yaml_path=yaml_path,
                remediation=(
                    "If this workflow does not need every push, add suitable branch, "
                    "path, or tag filters to the push trigger."
                ),
                **location_fields(workflow, yaml_path),
            )
        ]

    @staticmethod
    def _push_configuration(triggers: Any) -> Any:
        if triggers == "push":
            return True
        if isinstance(triggers, list):
            return True if "push" in triggers else _ABSENT
        if isinstance(triggers, Mapping):
            return triggers.get("push", _ABSENT)
        return _ABSENT
