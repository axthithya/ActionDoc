"""Enumerations used by ActionDoctor's public models."""

from enum import StrEnum


class Severity(StrEnum):
    """Severity assigned to a finding."""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RuleCategory(StrEnum):
    """Area of workflow quality addressed by a rule."""

    SECURITY = "security"
    COST = "cost"
    RELIABILITY = "reliability"
    MAINTAINABILITY = "maintainability"


class ScanStatus(StrEnum):
    """Completion state of a scan."""

    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


class HealthRating(StrEnum):
    """Human-readable interpretation of a numeric health score."""

    EXCELLENT = "Excellent"
    GOOD = "Good"
    NEEDS_ATTENTION = "Needs attention"
    POOR = "Poor"


class ScanCompleteness(StrEnum):
    """Whether every discovered workflow and rule evaluation succeeded."""

    COMPLETE = "complete"
    INCOMPLETE = "incomplete"


class FailureThreshold(StrEnum):
    """Finding severity that should make a CLI scan fail."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NEVER = "never"


class ReportFormat(StrEnum):
    """Supported scan-report representations."""

    TERMINAL = "terminal"
    JSON = "json"
    MARKDOWN = "markdown"
