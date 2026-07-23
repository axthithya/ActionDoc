"""Explicit, deterministic registry of ActionDoctor rules."""

import re
from collections.abc import Iterable

from actiondoctor.models import RuleCategory, Severity
from actiondoctor.models.finding import RULE_ID_PATTERN
from actiondoctor.rules.base import Rule
from actiondoctor.rules.maintainability import MissingWorkflowNameRule
from actiondoctor.rules.reliability import MissingJobsRule
from actiondoctor.rules.security import (
    BroadPermissionsRule,
    MissingExplicitPermissionsRule,
    PullRequestTargetCheckoutRule,
    UnpinnedActionRule,
    WorkflowSecretEnvironmentRule,
)

CATEGORY_PREFIXES = {
    RuleCategory.SECURITY: "SEC",
    RuleCategory.COST: "COST",
    RuleCategory.RELIABILITY: "REL",
    RuleCategory.MAINTAINABILITY: "MAINT",
}


class RuleRegistryError(ValueError):
    """Base class for invalid registry definitions or lookups."""


class DuplicateRuleIdError(RuleRegistryError):
    """Raised when two registered rules use the same public ID."""


class InvalidRuleError(RuleRegistryError):
    """Raised when rule metadata violates the public contract."""


class UnknownRuleIdError(RuleRegistryError):
    """Raised when a requested rule ID is not registered."""


class RuleRegistry:
    """Validate and expose an explicit collection of rule instances."""

    def __init__(self, rules: Iterable[Rule]) -> None:
        by_id: dict[str, Rule] = {}
        for rule in rules:
            self._validate_rule(rule)
            if rule.rule_id in by_id:
                raise DuplicateRuleIdError(f"Duplicate rule ID: {rule.rule_id}")
            by_id[rule.rule_id] = rule
        self._rules = tuple(by_id[rule_id] for rule_id in sorted(by_id))

    @property
    def rules(self) -> tuple[Rule, ...]:
        """Return all rules in deterministic rule-ID order."""
        return self._rules

    def filter_by_category(self, category: RuleCategory) -> tuple[Rule, ...]:
        """Return registered rules in one category."""
        return tuple(rule for rule in self._rules if rule.category is category)

    def filter_by_rule_ids(self, rule_ids: Iterable[str]) -> tuple[Rule, ...]:
        """Return requested rules in deterministic order or reject unknown IDs."""
        requested = set(rule_ids)
        unknown = requested.difference(rule.rule_id for rule in self._rules)
        if unknown:
            unknown_list = ", ".join(sorted(unknown))
            raise UnknownRuleIdError(f"Unknown rule ID: {unknown_list}")
        return tuple(rule for rule in self._rules if rule.rule_id in requested)

    @staticmethod
    def _validate_rule(rule: Rule) -> None:
        if (
            not isinstance(rule.rule_id, str)
            or re.fullmatch(RULE_ID_PATTERN, rule.rule_id) is None
        ):
            raise InvalidRuleError(f"Invalid rule ID: {rule.rule_id}")
        if not isinstance(rule.category, RuleCategory):
            raise InvalidRuleError(f"Invalid category for {rule.rule_id}")
        expected_prefix = CATEGORY_PREFIXES[rule.category]
        if not rule.rule_id.startswith(expected_prefix):
            raise InvalidRuleError(
                f"Rule ID {rule.rule_id} does not match category {rule.category.value}"
            )
        if not isinstance(rule.default_severity, Severity):
            raise InvalidRuleError(f"Invalid severity for {rule.rule_id}")
        if not isinstance(rule.title, str) or not rule.title.strip():
            raise InvalidRuleError(f"Rule {rule.rule_id} has an empty title")
        if not isinstance(rule.description, str) or not rule.description.strip():
            raise InvalidRuleError(f"Rule {rule.rule_id} has an empty description")


DEFAULT_RULES: tuple[Rule, ...] = (
    BroadPermissionsRule(),
    MissingExplicitPermissionsRule(),
    UnpinnedActionRule(),
    PullRequestTargetCheckoutRule(),
    WorkflowSecretEnvironmentRule(),
    MissingWorkflowNameRule(),
    MissingJobsRule(),
)
DEFAULT_REGISTRY = RuleRegistry(DEFAULT_RULES)
