"""Tests for deterministic, failure-isolating rule execution."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from actiondoctor.engine import RuleEngine
from actiondoctor.models import (
    Finding,
    RuleCategory,
    Severity,
    WorkflowFile,
)
from actiondoctor.registry import DEFAULT_REGISTRY
from actiondoctor.rules.maintainability import MissingWorkflowNameRule
from actiondoctor.rules.reliability import MissingJobsRule


def workflow(name: str, content: dict[str, Any]) -> WorkflowFile:
    """Create a parsed workflow with a portable relative path."""
    relative_path = f".github/workflows/{name}"
    return WorkflowFile(
        path=Path("repository") / relative_path,
        relative_path=relative_path,
        raw_text="",
        parsed_content=content,
    )


@dataclass
class FailingRule:
    """Test rule that always raises a sensitive-looking exception."""

    rule_id: str = "SEC001"
    title: str = "Failing Rule"
    description: str = "Raises to test isolation."
    category: RuleCategory = RuleCategory.SECURITY
    default_severity: Severity = Severity.HIGH

    def evaluate(self, workflow: WorkflowFile) -> list[Finding]:
        raise RuntimeError(r"secret at C:\private\repository")


def test_engine_runs_every_rule_across_multiple_workflows() -> None:
    """The execution count is rule/workflow evaluations, not distinct rules."""
    workflows = [
        workflow(
            "valid.yml",
            {"name": "CI", "permissions": {}, "jobs": {"test": {}}},
        ),
        workflow("incomplete.yml", {"permissions": {}}),
    ]

    result = RuleEngine().run(workflows, DEFAULT_REGISTRY.rules)

    assert result.rules_executed == 14
    assert [finding.rule_id for finding in result.findings] == [
        "REL001",
        "MAINT001",
    ]
    assert result.execution_errors == []


def test_engine_collects_multiple_findings_from_one_workflow() -> None:
    """Independent rules can report the same workflow."""
    result = RuleEngine().run(
        [workflow("incomplete.yml", {})],
        [MissingWorkflowNameRule(), MissingJobsRule()],
    )

    assert len(result.findings) == 2
    assert {finding.rule_id for finding in result.findings} == {
        "MAINT001",
        "REL001",
    }


def test_engine_returns_no_findings_for_valid_workflow() -> None:
    """A complete workflow remains clean under both demonstration rules."""
    result = RuleEngine().run(
        [
            workflow(
                "valid.yml",
                {"name": "CI", "permissions": {}, "jobs": {"test": {}}},
            )
        ],
        DEFAULT_REGISTRY.rules,
    )

    assert result.findings == []
    assert result.rules_executed == 7


def test_engine_isolates_rule_execution_failure() -> None:
    """One broken rule does not prevent later rule evaluations."""
    result = RuleEngine().run(
        [workflow("no-jobs.yml", {"name": "No Jobs"})],
        [FailingRule(), MissingJobsRule()],
    )

    assert result.rules_executed == 2
    assert [finding.rule_id for finding in result.findings] == ["REL001"]
    assert len(result.execution_errors) == 1
    error = result.execution_errors[0]
    assert error.rule_id == "SEC001"
    assert error.workflow_path == ".github/workflows/no-jobs.yml"
    assert error.error_type == "RuntimeError"
    assert error.error_message == "The rule raised an unexpected exception."
    assert "private" not in error.error_message


def test_engine_protects_shared_workflow_from_rule_mutation() -> None:
    """Each evaluation receives a deep copy of the parsed workflow."""

    class MutatingRule:
        rule_id = "MAINT001"
        title = "Mutator"
        description = "Mutates its isolated input."
        category = RuleCategory.MAINTAINABILITY
        default_severity = Severity.LOW

        def evaluate(self, candidate: WorkflowFile) -> list[Finding]:
            candidate.parsed_content["mutated"] = True
            return []

    class ObservingRule:
        rule_id = "MAINT002"
        title = "Observer"
        description = "Fails if it observes another rule's mutation."
        category = RuleCategory.MAINTAINABILITY
        default_severity = Severity.LOW

        def evaluate(self, candidate: WorkflowFile) -> list[Finding]:
            if "mutated" in candidate.parsed_content:
                raise AssertionError("shared mutation observed")
            return []

    original = workflow("valid.yml", {"name": "CI", "jobs": {"test": {}}})

    result = RuleEngine().run([original], [MutatingRule(), ObservingRule()])

    assert result.execution_errors == []
    assert "mutated" not in original.parsed_content


def test_engine_sorts_findings_deterministically() -> None:
    """Path, location, severity, ID, and title define public finding order."""

    class UnorderedRule:
        rule_id = "SEC001"
        title = "Unordered"
        description = "Returns intentionally unordered findings."
        category = RuleCategory.SECURITY
        default_severity = Severity.LOW

        def evaluate(self, candidate: WorkflowFile) -> list[Finding]:
            del candidate
            return [
                Finding(
                    rule_id="COST001",
                    title="B file",
                    description="test",
                    severity=Severity.LOW,
                    category=RuleCategory.COST,
                    file_path=Path(".github/workflows/b.yml"),
                    line=1,
                ),
                Finding(
                    rule_id="SEC001",
                    title="No line",
                    description="test",
                    severity=Severity.CRITICAL,
                    category=RuleCategory.SECURITY,
                    file_path=Path(".github/workflows/a.yml"),
                ),
                Finding(
                    rule_id="MAINT001",
                    title="Low",
                    description="test",
                    severity=Severity.LOW,
                    category=RuleCategory.MAINTAINABILITY,
                    file_path=Path(".github/workflows/a.yml"),
                    line=10,
                ),
                Finding(
                    rule_id="REL001",
                    title="High",
                    description="test",
                    severity=Severity.HIGH,
                    category=RuleCategory.RELIABILITY,
                    file_path=Path(".github/workflows/a.yml"),
                    line=10,
                ),
            ]

    result = RuleEngine().run(
        [workflow("source.yml", {"name": "CI", "jobs": {"test": {}}})],
        [UnorderedRule()],
    )

    assert [
        (finding.file_path.name, finding.rule_id) for finding in result.findings
    ] == [
        ("a.yml", "REL001"),
        ("a.yml", "MAINT001"),
        ("a.yml", "SEC001"),
        ("b.yml", "COST001"),
    ]


def test_engine_deduplicates_same_rule_and_yaml_location() -> None:
    """Identical reports for one rule/location appear only once."""

    class DuplicateRule:
        rule_id = "SEC001"
        title = "Duplicate"
        description = "Returns the same finding twice."
        category = RuleCategory.SECURITY
        default_severity = Severity.HIGH

        def evaluate(self, candidate: WorkflowFile) -> list[Finding]:
            finding = Finding(
                rule_id=self.rule_id,
                title=self.title,
                description=self.description,
                severity=self.default_severity,
                category=self.category,
                file_path=Path(candidate.relative_path),
                yaml_path="permissions",
            )
            return [finding, finding]

    result = RuleEngine().run(
        [workflow("duplicate.yml", {"name": "CI", "jobs": {"test": {}}})],
        [DuplicateRule()],
    )

    assert len(result.findings) == 1
