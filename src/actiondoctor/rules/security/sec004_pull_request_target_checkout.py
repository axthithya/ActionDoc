"""SEC004: detect risky pull_request_target checkout references."""

from collections.abc import Mapping
from pathlib import Path

from actiondoctor.models import Finding, RuleCategory, Severity, WorkflowFile
from actiondoctor.rules.security.helpers import has_trigger, iter_steps, location_fields

RISKY_PULL_REQUEST_REFS = (
    "github.event.pull_request.head.sha",
    "github.event.pull_request.head.ref",
    "github.head_ref",
)


class PullRequestTargetCheckoutRule:
    """Report checkout of likely untrusted PR code under pull_request_target."""

    rule_id = "SEC004"
    title = "Untrusted Pull Request Checkout Risk"
    description = (
        "A pull_request_target workflow appears to check out pull-request head code."
    )
    category = RuleCategory.SECURITY
    default_severity = Severity.CRITICAL

    def evaluate(self, workflow: WorkflowFile) -> list[Finding]:
        """Find risky checkout ref expressions under pull_request_target."""
        if not has_trigger(workflow, "pull_request_target"):
            return []

        findings: list[Finding] = []
        for context in iter_steps(workflow):
            uses = context.step.get("uses")
            if not isinstance(uses, str) or not self._is_checkout(uses):
                continue
            options = context.step.get("with")
            if not isinstance(options, Mapping):
                continue
            ref = options.get("ref")
            if not isinstance(ref, str) or not self._is_risky_ref(ref):
                continue

            yaml_path = f"{context.yaml_path}.with.ref"
            findings.append(
                Finding(
                    rule_id=self.rule_id,
                    title=self.title,
                    description=(
                        "`pull_request_target` runs in the base repository security "
                        "context, and this checkout appears to select untrusted "
                        "pull-request head code."
                    ),
                    severity=self.default_severity,
                    category=self.category,
                    file_path=Path(workflow.relative_path),
                    job_id=context.job_id,
                    yaml_path=yaml_path,
                    remediation=(
                        "Avoid checking out pull-request head code in "
                        "`pull_request_target`; use `pull_request` or isolate "
                        "untrusted code in an unprivileged job."
                    ),
                    **location_fields(workflow, yaml_path),
                )
            )
        return findings

    @staticmethod
    def _is_checkout(uses: str) -> bool:
        action = uses.strip().partition("@")[0].lower()
        return action == "actions/checkout"

    @staticmethod
    def _is_risky_ref(ref: str) -> bool:
        lowered = ref.lower()
        return any(risky_ref in lowered for risky_ref in RISKY_PULL_REQUEST_REFS)
