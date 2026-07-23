"""Tests for the foundation CLI."""

from pathlib import Path

from typer.testing import CliRunner

from actiondoctor import __version__
from actiondoctor.cli import app

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
    assert "ActionDoctor Scan" in result.stdout
    assert "Workflow files discovered: 2" in result.stdout
    assert "Successfully parsed: 2" in result.stdout
    assert "Failed to parse: 0" in result.stdout
    assert "Total rules executed: 4" in result.stdout
    assert "Total findings: 0" in result.stdout
    assert ".github/workflows/a-ci.yml" in result.stdout
    assert ".github/workflows/z-release.yaml" in result.stdout


def test_scan_help() -> None:
    """The scan command exposes help without doing work."""
    result = runner.invoke(app, ["scan", "--help"])

    assert result.exit_code == 0
    assert "Discover and parse GitHub Actions workflow files." in result.stdout


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
    assert "Total rules executed: 2" in result.stdout
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
    assert "Total rules executed: 2" in result.stdout
    assert "Total findings: 1" in result.stdout
    assert "Invalid YAML:" in result.stdout
    assert "MAINT001" in result.stdout
