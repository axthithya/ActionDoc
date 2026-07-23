"""Tests for the explicit rule registry."""

from dataclasses import dataclass

import pytest

from actiondoctor.models import Finding, RuleCategory, Severity, WorkflowFile
from actiondoctor.registry import (
    DuplicateRuleIdError,
    InvalidRuleError,
    RuleRegistry,
    UnknownRuleIdError,
)


@dataclass
class StubRule:
    """Minimal configurable rule used to validate registry behavior."""

    rule_id: str
    category: RuleCategory
    title: str = "Stub Rule"
    description: str = "A test-only rule."
    default_severity: Severity = Severity.LOW

    def evaluate(self, workflow: WorkflowFile) -> list[Finding]:
        return []


def test_registers_valid_rules_in_rule_id_order() -> None:
    """Input order does not affect public registry order."""
    registry = RuleRegistry(
        [
            StubRule("REL001", RuleCategory.RELIABILITY),
            StubRule("MAINT001", RuleCategory.MAINTAINABILITY),
            StubRule("COST001", RuleCategory.COST),
            StubRule("SEC001", RuleCategory.SECURITY),
        ]
    )

    assert [rule.rule_id for rule in registry.rules] == [
        "COST001",
        "MAINT001",
        "REL001",
        "SEC001",
    ]


def test_rejects_duplicate_rule_ids() -> None:
    """Rule IDs are unique public identifiers."""
    with pytest.raises(DuplicateRuleIdError, match="SEC001"):
        RuleRegistry(
            [
                StubRule("SEC001", RuleCategory.SECURITY),
                StubRule("SEC001", RuleCategory.SECURITY),
            ]
        )


@pytest.mark.parametrize(
    "rule_id",
    ["SEC01", "sec001", "OTHER001", "SEC000", "SEC1000", "SEC\u0660\u0660\u0661"],
)
def test_rejects_invalid_rule_ids(rule_id: str) -> None:
    """Only strict, nonzero category IDs with three digits are valid."""
    with pytest.raises(InvalidRuleError, match="Invalid rule ID"):
        RuleRegistry([StubRule(rule_id, RuleCategory.SECURITY)])


def test_rejects_category_prefix_mismatch() -> None:
    """A valid-looking ID must agree with its declared category."""
    with pytest.raises(InvalidRuleError, match="does not match category"):
        RuleRegistry([StubRule("SEC001", RuleCategory.COST)])


def test_filters_by_category() -> None:
    """Category filtering retains deterministic order."""
    registry = RuleRegistry(
        [
            StubRule("REL002", RuleCategory.RELIABILITY),
            StubRule("REL001", RuleCategory.RELIABILITY),
            StubRule("SEC001", RuleCategory.SECURITY),
        ]
    )

    selected = registry.filter_by_category(RuleCategory.RELIABILITY)

    assert [rule.rule_id for rule in selected] == ["REL001", "REL002"]


def test_filters_by_rule_id() -> None:
    """ID filtering returns only requested registered rules."""
    registry = RuleRegistry(
        [
            StubRule("REL001", RuleCategory.RELIABILITY),
            StubRule("MAINT001", RuleCategory.MAINTAINABILITY),
            StubRule("SEC001", RuleCategory.SECURITY),
        ]
    )

    selected = registry.filter_by_rule_ids(["SEC001", "MAINT001"])

    assert [rule.rule_id for rule in selected] == ["MAINT001", "SEC001"]


def test_rejects_unknown_filtered_rule_id() -> None:
    """Unknown configured IDs are never silently ignored."""
    registry = RuleRegistry([StubRule("SEC001", RuleCategory.SECURITY)])

    with pytest.raises(UnknownRuleIdError, match="REL999"):
        registry.filter_by_rule_ids(["SEC001", "REL999"])
