"""Tests for the foundation CLI."""

from typer.testing import CliRunner

from actiondoctor import __version__
from actiondoctor.cli import app

runner = CliRunner()


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


def test_scan_placeholder() -> None:
    """The placeholder scan is explicit and successful."""
    result = runner.invoke(app, ["scan"])

    assert result.exit_code == 0
    assert "scanner foundation is ready" in result.stdout
    assert "Workflow analysis is not implemented yet." in result.stdout


def test_scan_help() -> None:
    """The scan command exposes help without doing work."""
    result = runner.invoke(app, ["scan", "--help"])

    assert result.exit_code == 0
    assert "Show the scanner foundation status." in result.stdout
