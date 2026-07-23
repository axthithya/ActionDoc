"""Strongly typed contract implemented by every ActionDoctor rule."""

from typing import Protocol

from actiondoctor.models import Finding, RuleCategory, Severity, WorkflowFile


class Rule(Protocol):
    """A deterministic, side-effect-free workflow check."""

    rule_id: str
    title: str
    description: str
    category: RuleCategory
    default_severity: Severity

    def evaluate(self, workflow: WorkflowFile) -> list[Finding]:
        """Evaluate one parsed workflow and return its findings."""
        ...
