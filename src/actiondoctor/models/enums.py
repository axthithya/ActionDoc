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
