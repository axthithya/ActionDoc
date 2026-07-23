"""Reusable rule execution engine."""

from collections.abc import Iterable

from actiondoctor.models import (
    Finding,
    RuleEngineResult,
    RuleExecutionError,
    Severity,
    WorkflowFile,
)
from actiondoctor.rules.base import Rule

SEVERITY_SORT_ORDER = {
    Severity.CRITICAL: 0,
    Severity.HIGH: 1,
    Severity.MEDIUM: 2,
    Severity.LOW: 3,
    Severity.INFO: 4,
}


class RuleEngine:
    """Evaluate rules against workflows while isolating rule failures."""

    def run(
        self,
        workflows: Iterable[WorkflowFile],
        rules: Iterable[Rule],
    ) -> RuleEngineResult:
        """Run every rule against every workflow in deterministic order."""
        ordered_workflows = sorted(
            workflows,
            key=lambda workflow: (
                workflow.relative_path.casefold(),
                workflow.relative_path,
            ),
        )
        ordered_rules = sorted(rules, key=lambda rule: rule.rule_id)
        findings: list[Finding] = []
        execution_errors: list[RuleExecutionError] = []
        rules_executed = 0

        for workflow in ordered_workflows:
            for rule in ordered_rules:
                rules_executed += 1
                try:
                    isolated_workflow = workflow.model_copy(deep=True)
                    findings.extend(rule.evaluate(isolated_workflow))
                except Exception as error:
                    execution_errors.append(
                        RuleExecutionError(
                            rule_id=rule.rule_id,
                            workflow_path=workflow.relative_path,
                            error_type=type(error).__name__,
                            error_message="The rule raised an unexpected exception.",
                        )
                    )

        unique_findings = {
            self._finding_identity(finding): finding for finding in findings
        }
        return RuleEngineResult(
            findings=sorted(unique_findings.values(), key=self._finding_sort_key),
            execution_errors=execution_errors,
            rules_executed=rules_executed,
        )

    @staticmethod
    def _finding_sort_key(finding: Finding) -> tuple[object, ...]:
        return (
            finding.file_path.as_posix().casefold(),
            finding.file_path.as_posix(),
            finding.line if finding.line is not None else float("inf"),
            finding.column if finding.column is not None else float("inf"),
            SEVERITY_SORT_ORDER[finding.severity],
            finding.rule_id,
            finding.title.casefold(),
            finding.title,
        )

    @staticmethod
    def _finding_identity(finding: Finding) -> tuple[object, ...]:
        """Identify duplicate reports for the same rule and YAML location."""
        return (
            finding.rule_id,
            finding.file_path.as_posix(),
            finding.yaml_path,
            finding.line,
            finding.column,
            finding.job_id,
        )
