"""SEC001: detect overly broad top-level workflow permissions."""

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from actiondoctor.models import Finding, RuleCategory, Severity, WorkflowFile
from actiondoctor.rules.security.helpers import location_fields


class BroadPermissionsRule:
    """Report write-all or broadly write-only top-level permissions."""

    rule_id = "SEC001"
    title = "Overly Broad Workflow Permissions"
    description = "Top-level workflow permissions grant overly broad write access."
    category = RuleCategory.SECURITY
    default_severity = Severity.HIGH

    def evaluate(self, workflow: WorkflowFile) -> list[Finding]:
        """Evaluate the top-level permissions declaration."""
        permissions = workflow.parsed_content.get("permissions")
        severity: Severity | None = None
        detail = ""
        if isinstance(permissions, str) and permissions.strip().lower() == "write-all":
            severity = Severity.CRITICAL
            detail = "`permissions: write-all` grants write access to all scopes."
        elif self._is_broad_write_mapping(permissions):
            severity = Severity.HIGH
            detail = "Every declared permission scope is set to `write`."

        if severity is None:
            return []

        yaml_path = "permissions"
        return [
            Finding(
                rule_id=self.rule_id,
                title=self.title,
                description=detail,
                severity=severity,
                category=self.category,
                file_path=Path(workflow.relative_path),
                yaml_path=yaml_path,
                remediation=(
                    "Replace broad write access with the minimum read/write scopes "
                    "required by the workflow."
                ),
                **location_fields(workflow, yaml_path),
            )
        ]

    @staticmethod
    def _is_broad_write_mapping(value: Any) -> bool:
        if not isinstance(value, Mapping) or len(value) < 2:
            return False
        meaningful_values = [
            permission
            for scope, permission in value.items()
            if isinstance(scope, str) and isinstance(permission, str)
        ]
        return len(meaningful_values) == len(value) and all(
            permission.strip().lower() == "write" for permission in meaningful_values
        )
