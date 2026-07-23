"""Tests for the initial public models."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from actiondoctor.models import (
    Finding,
    RuleCategory,
    ScanResult,
    ScanStatus,
    Severity,
    WorkflowFile,
    WorkflowLoadResult,
)


def test_finding_accepts_valid_data() -> None:
    """A complete finding validates and retains typed enum values."""
    finding = Finding(
        rule_id="SEC001",
        title="Pin third-party actions",
        description="The action reference is mutable.",
        severity=Severity.HIGH,
        category=RuleCategory.SECURITY,
        file_path=Path(".github/workflows/ci.yml"),
        line=12,
        remediation="Pin the action to a full commit SHA.",
    )

    assert finding.rule_id == "SEC001"
    assert finding.severity is Severity.HIGH
    assert finding.line == 12


@pytest.mark.parametrize("rule_id", ["SEC1", "sec001", "OTHER001", "COST0001"])
def test_finding_rejects_invalid_rule_ids(rule_id: str) -> None:
    """Rule IDs must follow the documented category convention."""
    with pytest.raises(ValidationError):
        Finding(
            rule_id=rule_id,
            title="Invalid ID",
            description="This finding has an invalid ID.",
            severity=Severity.LOW,
            category=RuleCategory.SECURITY,
            file_path=Path("workflow.yml"),
        )


def test_finding_rejects_non_positive_line_number() -> None:
    """User-facing source line numbers are one-based."""
    with pytest.raises(ValidationError):
        Finding(
            rule_id="REL001",
            title="Invalid line",
            description="Line zero is not a valid source location.",
            severity=Severity.MEDIUM,
            category=RuleCategory.RELIABILITY,
            file_path=Path("workflow.yml"),
            line=0,
        )


def test_scan_result_defaults_to_clean_success() -> None:
    """An empty result has a bounded placeholder score."""
    result = ScanResult()

    assert result.scanned_files == []
    assert result.findings == []
    assert result.health_score == 100
    assert result.status is ScanStatus.SUCCESS


@pytest.mark.parametrize("health_score", [-1, 101])
def test_scan_result_rejects_score_outside_bounds(health_score: int) -> None:
    """Health scores are always between zero and one hundred."""
    with pytest.raises(ValidationError):
        ScanResult(health_score=health_score)


def test_workflow_load_result_is_serializable(tmp_path: Path) -> None:
    """Workflow boundary models support machine serialization."""
    workflow = WorkflowFile(
        path=tmp_path / "ci.yml",
        relative_path=".github/workflows/ci.yml",
        raw_text="name: CI\n",
        parsed_content={"name": "CI", "on": "push"},
    )
    result = WorkflowLoadResult(
        repository_path=tmp_path,
        workflow_directory=tmp_path / ".github" / "workflows",
        workflow_directory_exists=True,
        workflows=[workflow],
        discovered_file_count=1,
    )

    serialized = result.model_dump(mode="json")

    assert serialized["discovered_file_count"] == 1
    assert serialized["workflows"][0]["relative_path"] == (".github/workflows/ci.yml")
