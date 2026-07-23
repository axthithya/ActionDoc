"""SEC005: detect secrets assigned to workflow-level environment variables."""

import re
from collections.abc import Mapping
from pathlib import Path

from actiondoctor.models import Finding, RuleCategory, Severity, WorkflowFile
from actiondoctor.rules.security.helpers import location_fields

SECRET_REFERENCE = re.compile(r"\bsecrets\.[A-Za-z_][A-Za-z0-9_]*")


class WorkflowSecretEnvironmentRule:
    """Report broad workflow-level environment secret references."""

    rule_id = "SEC005"
    title = "Secret Exposed Through Workflow-Level Environment"
    description = "A workflow-level environment variable directly references a secret."
    category = RuleCategory.SECURITY
    default_severity = Severity.MEDIUM

    def evaluate(self, workflow: WorkflowFile) -> list[Finding]:
        """Inspect only top-level env entries, not job, step, or shell content."""
        environment = workflow.parsed_content.get("env")
        if not isinstance(environment, Mapping):
            return []

        findings: list[Finding] = []
        for variable, value in environment.items():
            if not isinstance(variable, str) or not isinstance(value, str):
                continue
            if SECRET_REFERENCE.search(value) is None:
                continue
            yaml_path = f"env.{variable}"
            findings.append(
                Finding(
                    rule_id=self.rule_id,
                    title=self.title,
                    description=(
                        f"Workflow-level environment variable `{variable}` directly "
                        "references a secret."
                    ),
                    severity=self.default_severity,
                    category=self.category,
                    file_path=Path(workflow.relative_path),
                    yaml_path=yaml_path,
                    remediation=(
                        "Move the secret reference to the smallest job or step scope "
                        "that requires it."
                    ),
                    **location_fields(workflow, yaml_path),
                )
            )
        return findings
