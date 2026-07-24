"""Tests for standalone Markdown report generation."""

from pathlib import Path

from actiondoctor.models import (
    Finding,
    RuleCategory,
    RuleExecutionError,
    ScanResult,
    Severity,
    WorkflowParseError,
)
from actiondoctor.reporting import MarkdownReporter
from actiondoctor.scoring import HealthScorer


def make_finding(path: Path, **fields: object) -> Finding:
    """Create a Markdown-focused finding."""
    return Finding(
        rule_id="SEC001",
        title=str(fields.get("title", "Test finding")),
        description=str(fields.get("description", "Test description.")),
        severity=Severity.HIGH,
        category=RuleCategory.SECURITY,
        file_path=path,
        line=fields.get("line"),
        job_id=fields.get("job_id"),
        yaml_path=fields.get("yaml_path"),
        remediation=fields.get("remediation"),
    )


def test_markdown_clean_report_has_summary_tables_and_no_findings(
    tmp_path: Path,
) -> None:
    rendered = MarkdownReporter().render(ScanResult(repository_path=tmp_path))

    assert rendered.startswith("# ActionDoc Report\n")
    assert rendered.endswith("\n")
    assert "\x1b[" not in rendered
    assert "- **Health score:** 100/100" in rendered
    assert "- **Completeness:** complete" in rendered
    assert "| Critical | 0 |" in rendered
    assert "| Security | 0 |" in rendered
    assert "No findings were detected." in rendered


def test_markdown_groups_findings_and_displays_context(tmp_path: Path) -> None:
    finding = make_finding(
        Path(".github/workflows/ci.yml"),
        line=8,
        job_id="build",
        yaml_path="jobs.build.steps[1].uses",
        remediation="Pin it.",
    )
    score = HealthScorer().score([finding])
    result = ScanResult(repository_path=tmp_path, findings=[finding], score=score)

    rendered = MarkdownReporter().render(result)

    assert rendered.count("### .github/workflows/ci.yml") == 1
    assert "#### HIGH `SEC001` - Test finding" in rendered
    assert "- **Location:** .github/workflows/ci.yml:8" in rendered
    assert "- **Job:** build" in rendered
    assert "- **Step index:** 1" in rendered
    assert r"- **YAML path:** jobs.build.steps\[1\].uses" in rendered
    assert "- **Description:** Test description." in rendered
    assert "- **Remediation:** Pin it." in rendered


def test_markdown_incomplete_warning_and_error_sections(tmp_path: Path) -> None:
    parse_error = WorkflowParseError(
        file_path=tmp_path / ".github" / "workflows" / "broken.yml",
        error_message="Invalid *YAML*",
        line=3,
    )
    execution_error = RuleExecutionError(
        rule_id="REL001",
        workflow_path=".github/workflows/ci.yml",
        error_type="RuntimeError",
        error_message="Safe message",
    )
    score = HealthScorer().score([], parse_error_count=1, execution_error_count=1)
    result = ScanResult(
        repository_path=tmp_path,
        parse_errors=[parse_error],
        rule_execution_errors=[execution_error],
        score=score,
    )

    rendered = MarkdownReporter().render(result)

    assert "> **Warning:** Incomplete analysis (2 errors)." in rendered
    assert "## Parse Errors" in rendered
    assert "Invalid \\*YAML\\*" in rendered
    assert "## Rule Execution Errors" in rendered
    assert "REL001" in rendered and "Safe message" in rendered


def test_markdown_escapes_user_controlled_values(tmp_path: Path) -> None:
    finding = make_finding(
        Path(".github/workflows/odd_[name].yml"),
        title="Risk *[value]*",
        description="Use `safe` | reviewed",
    )
    score = HealthScorer().score([finding])
    result = ScanResult(repository_path=tmp_path, findings=[finding], score=score)

    rendered = MarkdownReporter().render(result)

    assert "odd\\_\\[name\\].yml" in rendered
    assert "Risk \\*\\[value\\]\\*" in rendered
    assert "Use \\`safe\\` \\| reviewed" in rendered


def test_markdown_order_is_deterministic(tmp_path: Path) -> None:
    findings = [
        make_finding(Path(".github/workflows/z.yml")),
        make_finding(Path(".github/workflows/a.yml")),
    ]
    score = HealthScorer().score(findings)
    forward = ScanResult(repository_path=tmp_path, findings=findings, score=score)
    reverse = ScanResult(
        repository_path=tmp_path,
        findings=list(reversed(findings)),
        score=score,
    )

    assert MarkdownReporter().render(forward) == MarkdownReporter().render(reverse)
