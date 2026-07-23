"""SEC003: detect third-party step actions not pinned to a full commit SHA."""

import re
from pathlib import Path

from actiondoctor.models import Finding, RuleCategory, Severity, WorkflowFile
from actiondoctor.rules.security.helpers import iter_steps, location_fields

FULL_COMMIT_SHA = re.compile(r"^[0-9a-fA-F]{40}$")


class UnpinnedActionRule:
    """Report mutable third-party action references in workflow steps."""

    rule_id = "SEC003"
    title = "Third-Party Action Not Pinned to Commit SHA"
    description = "A third-party action uses a mutable reference."
    category = RuleCategory.SECURITY
    default_severity = Severity.HIGH

    def evaluate(self, workflow: WorkflowFile) -> list[Finding]:
        """Inspect mapping-shaped steps with scalar `uses` values."""
        findings: list[Finding] = []
        for context in iter_steps(workflow):
            uses = context.step.get("uses")
            if not isinstance(uses, str) or self._is_exempt_or_pinned(uses):
                continue
            yaml_path = f"{context.yaml_path}.uses"
            findings.append(
                Finding(
                    rule_id=self.rule_id,
                    title=self.title,
                    description=f"Action reference `{uses}` is not immutable.",
                    severity=self.default_severity,
                    category=self.category,
                    file_path=Path(workflow.relative_path),
                    job_id=context.job_id,
                    yaml_path=yaml_path,
                    remediation=(
                        "Pin the action to the full 40-character commit SHA reviewed "
                        "for use."
                    ),
                    **location_fields(workflow, yaml_path),
                )
            )
        return findings

    @staticmethod
    def _is_exempt_or_pinned(uses: str) -> bool:
        reference = uses.strip()
        if reference.startswith("./") or reference.lower().startswith("docker://"):
            return True
        if "@" not in reference:
            return False
        _, revision = reference.rsplit("@", maxsplit=1)
        return FULL_COMMIT_SHA.fullmatch(revision) is not None
