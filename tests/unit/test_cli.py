"""Tests for the foundation CLI."""

from pathlib import Path

from typer.testing import CliRunner

from actiondoctor import __version__
from actiondoctor.cli import app
from actiondoctor.models import RuleEngineResult, RuleExecutionError

runner = CliRunner()
FIXTURES = Path(__file__).parents[1] / "fixtures" / "repositories"


def test_help() -> None:
    """The root command exposes useful help."""
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "Audit GitHub Actions workflows." in result.stdout
    assert "scan" in result.stdout
    assert "version" in result.stdout


def test_version() -> None:
    """The version command prints the package version."""
    result = runner.invoke(app, ["version"])

    assert result.exit_code == 0
    assert result.stdout.strip() == __version__


def test_scan_valid_repository() -> None:
    """A valid repository prints counts and exits successfully."""
    result = runner.invoke(app, ["scan", str(FIXTURES / "multiple")])

    assert result.exit_code == 0
    assert "ActionDoc" in result.stdout
    assert "GitHub Actions Workflow Audit" in result.stdout
    assert "Workflow files discovered: 2" in result.stdout
    assert "Successfully parsed: 2" in result.stdout
    assert "Failed to parse: 0" in result.stdout
    assert "Total rules executed: 44" in result.stdout
    assert "Total findings: 0" in result.stdout
    assert ".github/workflows/a-ci.yml" in result.stdout
    assert ".github/workflows/z-release.yaml" in result.stdout


def test_scan_help() -> None:
    """The scan command exposes help without doing work."""
    result = runner.invoke(app, ["scan", "--help"])

    assert result.exit_code == 0
    assert "Discover, parse, and audit GitHub Actions workflow files." in result.stdout


def test_scan_help_documents_reporting_options() -> None:
    """Scan help exposes failure policy and plain-output controls."""
    result = runner.invoke(app, ["scan", "--help"])

    assert result.exit_code == 0
    assert "--fail-on" in result.stdout
    assert "--no-color" in result.stdout


def test_scan_mixed_repository_returns_one() -> None:
    """Any parse failure produces exit code one after showing partial success."""
    result = runner.invoke(app, ["scan", str(FIXTURES / "mixed")])

    assert result.exit_code == 1
    assert "Workflow files discovered: 2" in result.stdout
    assert "Successfully parsed: 1" in result.stdout
    assert "Failed to parse: 1" in result.stdout
    assert "good.yaml" in result.stdout
    assert "broken.yml" in result.stdout
    assert "Invalid YAML:" in result.stdout
    assert "line" in result.stdout
    assert "column" in result.stdout


def test_scan_missing_workflow_directory_returns_zero() -> None:
    """A repository with no workflow directory is a successful empty scan."""
    result = runner.invoke(app, ["scan", str(FIXTURES / "missing_workflows")])

    assert result.exit_code == 0
    assert "Workflow files discovered: 0" in result.stdout
    assert "No .github/workflows directory was found." in result.stdout


def test_scan_empty_workflow_directory_returns_zero() -> None:
    """A workflow directory with no YAML files is a successful empty scan."""
    result = runner.invoke(app, ["scan", str(FIXTURES / "empty_workflows")])

    assert result.exit_code == 0
    assert "contains no .yml or .yaml files" in result.stdout


def test_scan_invalid_repository_returns_two(tmp_path: Path) -> None:
    """An invalid repository path uses the documented application error code."""
    result = runner.invoke(app, ["scan", str(tmp_path / "missing")])

    assert result.exit_code == 2
    assert "Repository path does not exist" in result.stdout


def test_low_severity_finding_does_not_fail_scan() -> None:
    """MAINT001 is displayed but remains below the temporary threshold."""
    result = runner.invoke(app, ["scan", str(FIXTURES / "rules_low")])

    assert result.exit_code == 0
    assert "Total rules executed: 22" in result.stdout
    assert "Total findings: 1" in result.stdout
    assert "[LOW] MAINT001" in result.stdout
    assert "Missing Workflow Name" in result.stdout
    assert "Remediation:" in result.stdout


def test_high_severity_finding_fails_scan() -> None:
    """REL001 reaches the temporary high-severity failure threshold."""
    result = runner.invoke(app, ["scan", str(FIXTURES / "rules_high")])

    assert result.exit_code == 1
    assert "Total findings: 1" in result.stdout
    assert "[HIGH] REL001" in result.stdout
    assert "Missing Jobs" in result.stdout


def test_multiple_findings_are_grouped_by_workflow() -> None:
    """Both demonstration findings share one workflow heading."""
    result = runner.invoke(app, ["scan", str(FIXTURES / "rules_both")])

    assert result.exit_code == 1
    assert "Total findings: 2" in result.stdout
    assert result.stdout.count(".github/workflows/incomplete.yml") == 2
    assert "MAINT001" in result.stdout
    assert "REL001" in result.stdout


def test_mixed_parse_failure_and_finding() -> None:
    """Valid workflows are analyzed even when a neighboring file is malformed."""
    result = runner.invoke(app, ["scan", str(FIXTURES / "mixed_rules")])

    assert result.exit_code == 1
    assert "Successfully parsed: 1" in result.stdout
    assert "Failed to parse: 1" in result.stdout
    assert "Total rules executed: 22" in result.stdout
    assert "Total findings: 1" in result.stdout
    assert "Invalid YAML:" in result.stdout
    assert "MAINT001" in result.stdout


def test_security_findings_include_context_and_fail_scan() -> None:
    """Critical/high security findings show line, job, path, and remediation."""
    result = runner.invoke(app, ["scan", str(FIXTURES / "security_findings")])

    assert result.exit_code == 1
    assert "Total rules executed: 22" in result.stdout
    assert "SEC001" in result.stdout
    assert "[CRITICAL]" in result.stdout
    assert "SEC003" in result.stdout
    assert "[HIGH]" in result.stdout
    assert "line " in result.stdout
    assert "job build" in result.stdout
    assert "jobs.build.steps[0].uses" in result.stdout
    assert "Remediation:" in result.stdout


def test_cost_findings_are_shown_but_medium_does_not_fail_scan() -> None:
    """The current temporary threshold remains high despite cost findings."""
    result = runner.invoke(app, ["scan", str(FIXTURES / "cost_findings")])

    assert result.exit_code == 0
    assert "Total rules executed: 22" in result.stdout
    assert "Total findings: 3" in result.stdout
    assert "[MEDIUM] COST001" in result.stdout
    assert "[LOW] COST002" in result.stdout
    assert "[LOW] COST004" in result.stdout
    assert "job python" in result.stdout


def test_low_and_medium_reliability_findings_do_not_fail_scan() -> None:
    """REL003, REL004, and REL006 remain below the high threshold."""
    result = runner.invoke(app, ["scan", str(FIXTURES / "reliability_findings")])

    assert result.exit_code == 0
    assert "Total rules executed: 22" in result.stdout
    assert "Total findings: 3" in result.stdout
    assert "[MEDIUM] REL003" in result.stdout
    assert "[LOW] REL004" in result.stdout
    assert "[LOW] REL006" in result.stdout
    assert "job test" in result.stdout


def test_job_level_continue_on_error_fails_scan() -> None:
    """A high job-level REL005 finding reaches the current threshold."""
    result = runner.invoke(app, ["scan", str(FIXTURES / "reliability_job_failure")])

    assert result.exit_code == 1
    assert "Total findings: 1" in result.stdout
    assert "[HIGH] REL005" in result.stdout
    assert "jobs.experimental.continue-on-error" in result.stdout


def test_step_level_continue_on_error_does_not_fail_scan() -> None:
    """A medium step-level REL005 finding remains below the threshold."""
    result = runner.invoke(app, ["scan", str(FIXTURES / "reliability_step_failure")])

    assert result.exit_code == 0
    assert "Total findings: 1" in result.stdout
    assert "[MEDIUM] REL005" in result.stdout
    assert "jobs.test.steps[0].continue-on-error" in result.stdout


def test_maintainability_findings_display_without_failing_scan() -> None:
    """Low maintainability findings are shown below the high threshold."""
    result = runner.invoke(app, ["scan", str(FIXTURES / "maintainability_findings")])

    assert result.exit_code == 0
    assert "Total rules executed: 22" in result.stdout
    assert "Total findings: 3" in result.stdout
    assert "[LOW] MAINT002" in result.stdout
    assert "[LOW] MAINT003" in result.stdout
    assert "[LOW] MAINT005" in result.stdout
    assert "jobs.test.steps[0].name" in result.stdout


def test_critical_threshold_ignores_high_finding() -> None:
    """A critical threshold does not fail for a high-only repository."""
    result = runner.invoke(
        app,
        ["scan", str(FIXTURES / "rules_high"), "--fail-on", "critical"],
    )

    assert result.exit_code == 0


def test_medium_threshold_fails_for_cost_finding() -> None:
    """A medium threshold fails when a medium cost finding is present."""
    result = runner.invoke(
        app,
        ["scan", str(FIXTURES / "cost_findings"), "--fail-on", "medium"],
    )

    assert result.exit_code == 1


def test_low_threshold_fails_for_maintainability_finding() -> None:
    """A low threshold includes low-severity findings."""
    result = runner.invoke(
        app,
        ["scan", str(FIXTURES / "rules_low"), "--fail-on", "low"],
    )

    assert result.exit_code == 1


def test_never_threshold_ignores_findings() -> None:
    """Never disables finding-based failure without hiding findings."""
    result = runner.invoke(
        app,
        ["scan", str(FIXTURES / "security_findings"), "--fail-on", "never"],
    )

    assert result.exit_code == 0
    assert "SEC001" in result.stdout


def test_never_threshold_does_not_ignore_parse_errors() -> None:
    """Analysis errors fail independently of the finding threshold."""
    result = runner.invoke(
        app,
        ["scan", str(FIXTURES / "mixed"), "--fail-on", "never"],
    )

    assert result.exit_code == 1
    assert "Status" in result.stdout
    assert "Incomplete" in result.stdout


def test_never_threshold_does_not_ignore_rule_errors(monkeypatch: object) -> None:
    """An isolated rule crash fails even when findings never fail."""

    def failed_run(*_args: object, **_kwargs: object) -> RuleEngineResult:
        return RuleEngineResult(
            findings=[],
            execution_errors=[
                RuleExecutionError(
                    rule_id="REL001",
                    workflow_path=".github/workflows/a-ci.yml",
                    error_type="RuntimeError",
                    error_message="test failure",
                )
            ],
            rules_executed=22,
        )

    monkeypatch.setattr("actiondoctor.cli.RuleEngine.run", failed_run)  # type: ignore[attr-defined]
    result = runner.invoke(
        app,
        ["scan", str(FIXTURES / "multiple"), "--fail-on", "never"],
    )

    assert result.exit_code == 1
    assert "Rule execution errors" in result.stdout
    assert "Incomplete" in result.stdout


def test_invalid_failure_threshold_is_a_usage_error() -> None:
    """Typer rejects unsupported threshold values with exit code two."""
    result = runner.invoke(
        app,
        ["scan", str(FIXTURES / "multiple"), "--fail-on", "info"],
    )

    assert result.exit_code == 2


def test_no_color_output_contains_no_ansi_sequences() -> None:
    """Plain terminal mode is safe for logs and unsupported terminals."""
    result = runner.invoke(
        app,
        ["scan", str(FIXTURES / "rules_low"), "--no-color"],
    )

    assert result.exit_code == 0
    assert "\x1b[" not in result.stdout


def test_scan_displays_score_rating_and_breakdowns() -> None:
    """The CLI explains the score alongside category and severity counts."""
    result = runner.invoke(app, ["scan", str(FIXTURES / "rules_both")])

    assert "Health score" in result.stdout
    assert "89/100" in result.stdout
    assert "Health rating" in result.stdout
    assert "reliability: 1" in result.stdout
    assert "high: 1" in result.stdout
