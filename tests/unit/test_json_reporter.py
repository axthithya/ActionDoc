"""Tests for the stable JSON report contract."""

import json
from pathlib import Path

from actiondoctor import __version__
from actiondoctor.models import (
    Finding,
    RuleCategory,
    RuleExecutionError,
    ScanCompleteness,
    ScanResult,
    Severity,
    WorkflowParseError,
)
from actiondoctor.reporting import JsonReporter
from actiondoctor.scoring import HealthScorer


def make_finding(
    path: Path,
    *,
    rule_id: str = "SEC001",
    severity: Severity = Severity.HIGH,
    category: RuleCategory = RuleCategory.SECURITY,
    **fields: object,
) -> Finding:
    """Create a finding with optional public fields."""
    return Finding(
        rule_id=rule_id,
        title=str(fields.get("title", "Test finding")),
        description=str(fields.get("description", "Test description.")),
        severity=severity,
        category=category,
        file_path=path,
        line=fields.get("line"),
        column=fields.get("column"),
        job_id=fields.get("job_id"),
        yaml_path=fields.get("yaml_path"),
        remediation=fields.get("remediation"),
        documentation_url=fields.get("documentation_url"),
    )


def test_json_clean_scan_has_stable_schema_and_trailing_newline(
    tmp_path: Path,
) -> None:
    result = ScanResult(repository_path=tmp_path, active_rules=22)

    rendered = JsonReporter().render(result)
    document = json.loads(rendered)

    assert rendered.endswith("\n")
    assert "\x1b[" not in rendered
    assert document["schema_version"] == "1.0"
    assert document["actiondoctor_version"] == __version__
    assert document["completeness"] == "complete"
    assert document["health_score"] == 100
    assert document["finding_count"] == 0
    assert document["findings"] == []


def test_json_contains_score_summaries_and_optional_finding_fields(
    tmp_path: Path,
) -> None:
    workflow = tmp_path / ".github" / "workflows" / "ci.yml"
    finding = make_finding(
        workflow,
        line=7,
        column=9,
        job_id="build",
        yaml_path="jobs.build.steps[2].uses",
        remediation="Pin it.",
        documentation_url="https://example.test/SEC001",
    )
    score = HealthScorer().score([finding])
    result = ScanResult(
        repository_path=tmp_path,
        workflows_discovered=1,
        workflows_parsed=1,
        findings=[finding],
        active_rules=22,
        rule_evaluations=22,
        score=score,
    )

    document = json.loads(JsonReporter().render(result))
    exported = document["findings"][0]

    assert document["health_score"] == 90
    assert document["raw_penalty"] == 10
    assert document["capped_penalty"] == 10
    assert document["severity_summary"]["high"] == 1
    assert document["category_summary"]["security"] == 1
    assert document["penalty_by_severity"]["high"] == 10
    assert document["penalty_by_rule_id"] == {"SEC001": 10}
    assert exported["file"] == ".github/workflows/ci.yml"
    assert not Path(exported["file"]).is_absolute()
    assert exported["step_index"] == 2
    assert exported["step_name"] is None
    assert exported["documentation_url"].endswith("SEC001")


def test_json_incomplete_scan_keeps_errors_separate(tmp_path: Path) -> None:
    parse_error = WorkflowParseError(
        file_path=tmp_path / ".github" / "workflows" / "broken.yml",
        error_message="Invalid YAML",
        line=4,
        column=2,
    )
    execution_error = RuleExecutionError(
        rule_id="REL001",
        workflow_path=".github/workflows/ci.yml",
        error_type="RuntimeError",
        error_message="The rule raised an unexpected exception.",
    )
    score = HealthScorer().score([], parse_error_count=1, execution_error_count=1)
    result = ScanResult(
        repository_path=tmp_path,
        workflows_discovered=2,
        workflows_parsed=1,
        parse_errors=[parse_error],
        rule_execution_errors=[execution_error],
        score=score,
    )

    document = json.loads(JsonReporter().render(result))

    assert document["completeness"] == ScanCompleteness.INCOMPLETE.value
    assert document["health_score"] == 100
    assert document["parse_error_count"] == 1
    assert document["rule_execution_error_count"] == 1
    assert document["parse_errors"][0]["file"] == (".github/workflows/broken.yml")
    assert document["rule_execution_errors"][0]["rule_id"] == "REL001"


def test_json_optional_values_are_consistently_null(tmp_path: Path) -> None:
    finding = make_finding(Path(".github/workflows/ci.yml"))
    score = HealthScorer().score([finding])
    result = ScanResult(repository_path=tmp_path, findings=[finding], score=score)

    exported = json.loads(JsonReporter().render(result))["findings"][0]

    for field in (
        "line",
        "column",
        "job_id",
        "step_index",
        "step_name",
        "yaml_path",
        "remediation",
        "documentation_url",
    ):
        assert exported[field] is None


def test_json_order_is_deterministic(tmp_path: Path) -> None:
    first = make_finding(
        Path(".github/workflows/z.yml"),
        rule_id="MAINT001",
        severity=Severity.LOW,
        category=RuleCategory.MAINTAINABILITY,
    )
    second = make_finding(Path(".github/workflows/a.yml"), rule_id="SEC002")
    findings = [first, second]
    score = HealthScorer().score(findings)
    forward = ScanResult(repository_path=tmp_path, findings=findings, score=score)
    reverse = ScanResult(
        repository_path=tmp_path,
        findings=list(reversed(findings)),
        score=score,
    )

    assert JsonReporter().render(forward) == JsonReporter().render(reverse)
