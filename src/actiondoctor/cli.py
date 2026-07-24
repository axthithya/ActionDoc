"""Command-line interface for ActionDoctor."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.text import Text

from actiondoctor import __version__
from actiondoctor.engine import RuleEngine
from actiondoctor.models import (
    FailureThreshold,
    ReportFormat,
    ScanResult,
    ScanStatus,
    Severity,
)
from actiondoctor.parser import InvalidRepositoryError, WorkflowLoader
from actiondoctor.registry import DEFAULT_REGISTRY
from actiondoctor.reporting import (
    JsonReporter,
    MarkdownReporter,
    ReportWriteError,
    TerminalReporter,
    write_report_atomic,
)
from actiondoctor.scoring import HealthScorer

SEVERITY_RANK = {
    Severity.LOW: 1,
    Severity.MEDIUM: 2,
    Severity.HIGH: 3,
    Severity.CRITICAL: 4,
}

app = typer.Typer(
    help="Audit GitHub Actions workflows.",
    no_args_is_help=True,
    pretty_exceptions_show_locals=False,
)


@app.command()
def version() -> None:
    """Print the installed ActionDoctor version."""
    typer.echo(__version__)


@app.command()
def scan(
    repository: Annotated[
        Path,
        typer.Argument(
            help="Repository whose .github/workflows directory should be scanned."
        ),
    ] = Path("."),
    fail_on: Annotated[
        FailureThreshold,
        typer.Option(
            "--fail-on",
            case_sensitive=False,
            help="Lowest finding severity that produces exit code 1.",
        ),
    ] = FailureThreshold.HIGH,
    no_color: Annotated[
        bool,
        typer.Option("--no-color", help="Disable ANSI colors in terminal output."),
    ] = False,
    report_format: Annotated[
        ReportFormat,
        typer.Option(
            "--format",
            case_sensitive=False,
            help="Report format written to the terminal or output file.",
        ),
    ] = ReportFormat.TERMINAL,
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            help="Write a JSON or Markdown report atomically to this path.",
        ),
    ] = None,
) -> None:
    """Discover, parse, and audit GitHub Actions workflow files."""
    if output is not None and report_format is ReportFormat.TERMINAL:
        raise typer.BadParameter(
            "--output requires --format json or --format markdown",
            param_hint="--output",
        )
    console = Console(
        no_color=no_color,
        color_system=None if no_color else "auto",
    )
    try:
        load_result = WorkflowLoader().load_repository(repository)
        engine_result = RuleEngine().run(load_result.workflows, DEFAULT_REGISTRY.rules)
        score = HealthScorer().score(
            engine_result.findings,
            parse_error_count=len(load_result.parse_errors),
            execution_error_count=len(engine_result.execution_errors),
        )
        scan_result = ScanResult(
            repository_path=load_result.repository_path,
            workflow_directory_exists=load_result.workflow_directory_exists,
            workflows_discovered=load_result.discovered_file_count,
            workflows_parsed=load_result.successful_count,
            scanned_files=[
                Path(workflow.relative_path) for workflow in load_result.workflows
            ],
            parse_errors=load_result.parse_errors,
            findings=engine_result.findings,
            rule_execution_errors=engine_result.execution_errors,
            active_rules=len(DEFAULT_REGISTRY.rules),
            rule_evaluations=engine_result.rules_executed,
            score=score,
            status=(
                ScanStatus.PARTIAL
                if load_result.parse_errors or engine_result.execution_errors
                else ScanStatus.SUCCESS
            ),
        )
        _emit_report(scan_result, report_format, output, console)
    except InvalidRepositoryError as error:
        console.print(Text(f"Error: {error}", style="bold red"))
        raise typer.Exit(code=2) from error
    except ReportWriteError as error:
        console.print(Text(f"Error: {error}", style="bold red"))
        raise typer.Exit(code=2) from error
    except Exception as error:
        console.print(Text(f"Unexpected error: {error}", style="bold red"))
        raise typer.Exit(code=2) from error

    if (
        scan_result.parse_errors
        or scan_result.rule_execution_errors
        or _threshold_reached(scan_result, fail_on)
    ):
        raise typer.Exit(code=1)


def _threshold_reached(result: ScanResult, threshold: FailureThreshold) -> bool:
    """Return whether any finding meets the requested failure threshold."""
    if threshold is FailureThreshold.NEVER:
        return False
    minimum_rank = SEVERITY_RANK[Severity(threshold.value)]
    return any(
        SEVERITY_RANK.get(finding.severity, 0) >= minimum_rank
        for finding in result.findings
    )


def _emit_report(
    result: ScanResult,
    report_format: ReportFormat,
    output: Path | None,
    console: Console,
) -> None:
    """Render exactly one selected report and optionally write it atomically."""
    if report_format is ReportFormat.TERMINAL:
        TerminalReporter(console).render(result)
        return

    rendered = (
        JsonReporter().render(result)
        if report_format is ReportFormat.JSON
        else MarkdownReporter().render(result)
    )
    if output is None:
        typer.echo(rendered, nl=False)
        return

    write_report_atomic(output, rendered)
    typer.echo(f"Wrote {report_format.value} report to {output}")
