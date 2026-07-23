"""Command-line interface for ActionDoctor."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.text import Text

from actiondoctor import __version__
from actiondoctor.engine import RuleEngine
from actiondoctor.models import FailureThreshold, ScanResult, ScanStatus, Severity
from actiondoctor.parser import InvalidRepositoryError, WorkflowLoader
from actiondoctor.registry import DEFAULT_REGISTRY
from actiondoctor.reporting import TerminalReporter
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
) -> None:
    """Discover, parse, and audit GitHub Actions workflow files."""
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
        TerminalReporter(console).render(scan_result)
    except InvalidRepositoryError as error:
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
