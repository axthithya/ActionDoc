"""Tests for the dedicated Rich terminal reporter."""

from io import StringIO
from pathlib import Path

from rich.console import Console

from actiondoctor.models import (
    Finding,
    RuleCategory,
    RuleExecutionError,
    ScanResult,
    Severity,
    WorkflowParseError,
)
from actiondoctor.reporting import TerminalReporter
from actiondoctor.scoring import HealthScorer


def test_report_contains_score_breakdowns_details_and_errors() -> None:
    output = StringIO()
    console = Console(file=output, no_color=True, width=120)
    finding = Finding(
        rule_id="SEC001",
        title="Security issue",
        description="Unsafe behavior.",
        severity=Severity.HIGH,
        category=RuleCategory.SECURITY,
        file_path=Path(".github/workflows/ci.yml"),
        line=3,
        remediation="Use the safe form.",
    )
    parse_error = WorkflowParseError(
        file_path=Path("repo/.github/workflows/broken.yml"),
        error_message="Invalid YAML",
        line=4,
        column=2,
    )
    execution_error = RuleExecutionError(
        rule_id="REL001",
        workflow_path=".github/workflows/ci.yml",
        error_type="RuntimeError",
        error_message="boom",
    )
    score = HealthScorer().score(
        [finding], parse_error_count=1, execution_error_count=1
    )
    result = ScanResult(
        repository_path=Path("repo"),
        workflows_discovered=2,
        workflows_parsed=1,
        scanned_files=[Path(".github/workflows/ci.yml")],
        parse_errors=[parse_error],
        findings=[finding],
        rule_execution_errors=[execution_error],
        active_rules=22,
        rule_evaluations=22,
        score=score,
    )

    TerminalReporter(console).render(result)
    rendered = output.getvalue()

    assert "ActionDoc" in rendered
    assert "GitHub Actions Workflow Audit" in rendered
    assert "Health score" in rendered and "90/100" in rendered
    assert "Incomplete" in rendered
    assert "security: 1" in rendered
    assert "high: 1" in rendered
    assert "Description: Unsafe behavior." in rendered
    assert "Remediation: Use the safe form." in rendered
    assert "Workflow parse errors" in rendered
    assert "Rule execution errors" in rendered


def test_no_color_console_emits_no_ansi_sequences() -> None:
    output = StringIO()
    console = Console(
        file=output,
        force_terminal=True,
        color_system=None,
        no_color=True,
    )

    TerminalReporter(console).render(ScanResult())

    assert "\x1b[" not in output.getvalue()
