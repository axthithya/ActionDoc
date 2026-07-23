"""Tests for the two demonstration rules."""

from pathlib import Path
from typing import Any

import pytest

from actiondoctor.models import Severity, WorkflowFile
from actiondoctor.rules.maintainability import MissingWorkflowNameRule
from actiondoctor.rules.reliability import MissingJobsRule


def workflow(content: dict[str, Any]) -> WorkflowFile:
    """Create a small parsed workflow for direct rule tests."""
    return WorkflowFile(
        path=Path("repository/.github/workflows/test.yml"),
        relative_path=".github/workflows/test.yml",
        raw_text="",
        parsed_content=content,
    )


@pytest.mark.parametrize("name", [None, "", "   "])
def test_maint001_reports_missing_or_empty_name(name: str | None) -> None:
    """MAINT001 treats absent, null, and blank names as missing."""
    content: dict[str, Any] = {"jobs": {"test": {}}}
    if name is not None:
        content["name"] = name

    findings = MissingWorkflowNameRule().evaluate(workflow(content))

    assert len(findings) == 1
    assert findings[0].rule_id == "MAINT001"
    assert findings[0].severity is Severity.LOW
    assert findings[0].yaml_path == "name"
    assert findings[0].remediation is not None


def test_maint001_accepts_non_empty_name() -> None:
    """A named workflow has no MAINT001 finding."""
    findings = MissingWorkflowNameRule().evaluate(
        workflow({"name": "CI", "jobs": {"test": {}}})
    )

    assert findings == []


@pytest.mark.parametrize("jobs", [None, {}, [], "invalid"])
def test_rel001_reports_missing_empty_or_invalid_jobs(jobs: Any) -> None:
    """REL001 requires a non-empty mapping rather than merely a jobs key."""
    content: dict[str, Any] = {"name": "CI"}
    if jobs is not None:
        content["jobs"] = jobs

    findings = MissingJobsRule().evaluate(workflow(content))

    assert len(findings) == 1
    assert findings[0].rule_id == "REL001"
    assert findings[0].severity is Severity.HIGH
    assert findings[0].yaml_path == "jobs"
    assert findings[0].remediation is not None


def test_rel001_accepts_non_empty_jobs_mapping() -> None:
    """At least one mapped job satisfies REL001."""
    findings = MissingJobsRule().evaluate(
        workflow({"name": "CI", "jobs": {"test": {"runs-on": "ubuntu-latest"}}})
    )

    assert findings == []
