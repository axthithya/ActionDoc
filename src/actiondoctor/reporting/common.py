"""Shared deterministic projection helpers for public reports."""

import re
from contextlib import suppress
from pathlib import Path

from actiondoctor.models import Finding, ScanResult, Severity
from actiondoctor.models.rule import RuleExecutionError
from actiondoctor.models.workflow import WorkflowParseError

STEP_INDEX_PATTERN = re.compile(r"(?:^|\.)steps\[(\d+)\]")
SEVERITY_ORDER = {
    Severity.CRITICAL: 0,
    Severity.HIGH: 1,
    Severity.MEDIUM: 2,
    Severity.LOW: 3,
    Severity.INFO: 4,
}


def portable_path(path: Path | str, result: ScanResult) -> str:
    """Return a POSIX-style path relative to the repository when possible."""
    candidate = Path(path)
    if result.repository_path is not None:
        with suppress(ValueError):
            candidate = candidate.relative_to(result.repository_path)
    return candidate.as_posix()


def repository_path(result: ScanResult) -> str:
    """Return the selected repository path with stable separators."""
    if result.repository_path is None:
        return "unknown"
    return result.repository_path.as_posix()


def sorted_findings(result: ScanResult) -> list[Finding]:
    """Return findings in a reporter-independent deterministic order."""
    return sorted(
        result.findings,
        key=lambda finding: (
            portable_path(finding.file_path, result).casefold(),
            portable_path(finding.file_path, result),
            finding.line is None,
            finding.line or 0,
            finding.column is None,
            finding.column or 0,
            SEVERITY_ORDER[finding.severity],
            finding.rule_id,
            finding.title.casefold(),
            finding.title,
        ),
    )


def sorted_parse_errors(result: ScanResult) -> list[WorkflowParseError]:
    """Return parse errors in stable portable-path and location order."""
    return sorted(
        result.parse_errors,
        key=lambda error: (
            portable_path(error.file_path, result).casefold(),
            portable_path(error.file_path, result),
            error.line is None,
            error.line or 0,
            error.column is None,
            error.column or 0,
            error.error_message,
        ),
    )


def sorted_execution_errors(result: ScanResult) -> list[RuleExecutionError]:
    """Return safe rule errors in stable path and rule-ID order."""
    return sorted(
        result.rule_execution_errors,
        key=lambda error: (
            portable_path(error.workflow_path, result).casefold(),
            portable_path(error.workflow_path, result),
            error.rule_id,
            error.error_type,
        ),
    )


def step_index(yaml_path: str | None) -> int | None:
    """Extract a zero-based step index already present in a finding path."""
    if yaml_path is None:
        return None
    match = STEP_INDEX_PATTERN.search(yaml_path)
    return int(match.group(1)) if match else None
