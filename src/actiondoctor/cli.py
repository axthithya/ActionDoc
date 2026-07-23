"""Command-line interface for ActionDoctor."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.text import Text

from actiondoctor import __version__
from actiondoctor.engine import RuleEngine
from actiondoctor.models import RuleEngineResult, Severity, WorkflowLoadResult
from actiondoctor.parser import InvalidRepositoryError, WorkflowLoader
from actiondoctor.registry import DEFAULT_REGISTRY

FAILURE_SEVERITIES = frozenset({Severity.HIGH, Severity.CRITICAL})

app = typer.Typer(
    help="Audit GitHub Actions workflows.",
    no_args_is_help=True,
    pretty_exceptions_show_locals=False,
)
console = Console()


@app.command()
def version() -> None:
    """Print the installed ActionDoctor version."""
    typer.echo(__version__)


@app.command()
def scan(
    repository: Annotated[
        Path,
        typer.Argument(
            help="Repository whose .github/workflows directory should be scanned.",
        ),
    ] = Path("."),
) -> None:
    """Discover and parse GitHub Actions workflow files."""
    try:
        result = WorkflowLoader().load_repository(repository)
        rule_result = RuleEngine().run(result.workflows, DEFAULT_REGISTRY.rules)
        _render_scan_result(result, rule_result)
    except InvalidRepositoryError as error:
        console.print(Text(f"Error: {error}", style="bold red"))
        raise typer.Exit(code=2) from error
    except Exception as error:
        console.print(Text(f"Unexpected error: {error}", style="bold red"))
        raise typer.Exit(code=2) from error

    threshold_reached = any(
        finding.severity in FAILURE_SEVERITIES for finding in rule_result.findings
    )
    if result.parse_errors or rule_result.execution_errors or threshold_reached:
        raise typer.Exit(code=1)


def _render_scan_result(
    result: WorkflowLoadResult,
    rule_result: RuleEngineResult,
) -> None:
    """Render the parsing and rule-engine terminal summary."""
    console.print()
    console.print("[bold]ActionDoctor Scan[/bold]")
    console.print()
    console.print(Text(f"Repository: {result.repository_path}"))
    console.print(f"Workflow files discovered: {result.discovered_file_count}")
    console.print(f"Successfully parsed: {result.successful_count}")
    console.print(f"Failed to parse: {result.failed_count}")
    console.print(f"Total rules executed: {rule_result.rules_executed}")
    console.print(f"Total findings: {len(rule_result.findings)}")
    console.print(f"Rule execution failures: {len(rule_result.execution_errors)}")
    console.print()

    if not result.workflow_directory_exists:
        console.print(
            "No .github/workflows directory was found. There are no workflows to parse."
        )
        _render_rule_results(rule_result)
        return
    if result.discovered_file_count == 0:
        console.print(
            "The .github/workflows directory contains no .yml or .yaml files."
        )
        _render_rule_results(rule_result)
        return

    entries: list[tuple[Path, Text]] = []
    for workflow in result.workflows:
        entries.append(
            (
                workflow.path,
                Text.assemble(
                    (_terminal_marker("✓ ", "[OK] "), "green"),
                    workflow.relative_path,
                ),
            )
        )
    for error in result.parse_errors:
        message = error.error_message
        if error.line is not None:
            message += f" at line {error.line}"
            if error.column is not None:
                message += f", column {error.column}"
        relative_path = error.file_path.relative_to(result.repository_path).as_posix()
        entries.append(
            (
                error.file_path,
                Text.assemble(
                    (_terminal_marker("✗ ", "[ERROR] "), "red"),
                    relative_path,
                    " — ",
                    message,
                ),
            )
        )

    for _, line in sorted(
        entries,
        key=lambda entry: (
            entry[0].name.casefold(),
            entry[0].name,
        ),
    ):
        console.print(line)

    _render_rule_results(rule_result)


def _render_rule_results(result: RuleEngineResult) -> None:
    """Render findings grouped by their portable workflow path."""
    if result.findings:
        console.print()
        console.print("[bold]Findings[/bold]")
        current_path: str | None = None
        for finding in result.findings:
            workflow_path = finding.file_path.as_posix()
            if workflow_path != current_path:
                console.print()
                console.print(Text(workflow_path, style="bold"))
                current_path = workflow_path
            console.print(
                Text.assemble(
                    "  ",
                    (f"[{finding.severity.value.upper()}] ", "yellow"),
                    (finding.rule_id, "cyan"),
                    f" — {finding.title}",
                )
            )
            context: list[str] = []
            if finding.line is not None:
                location = f"line {finding.line}"
                if finding.column is not None:
                    location += f", column {finding.column}"
                context.append(location)
            if finding.job_id is not None:
                context.append(f"job {finding.job_id}")
            if finding.yaml_path is not None:
                context.append(finding.yaml_path)
            if context:
                console.print(Text(f"    Location: {'; '.join(context)}"))
            if finding.remediation is not None:
                console.print(Text(f"    Remediation: {finding.remediation}"))

    if result.execution_errors:
        console.print()
        console.print("[bold red]Rule execution failures[/bold red]")
        for error in result.execution_errors:
            console.print(
                Text(
                    f"  {error.workflow_path}: {error.rule_id} "
                    f"failed with {error.error_type} — {error.error_message}"
                )
            )


def _terminal_marker(preferred: str, fallback: str) -> str:
    """Return a status marker supported by the active terminal encoding."""
    encoding = getattr(console.file, "encoding", None) or "utf-8"
    try:
        preferred.encode(encoding)
    except (LookupError, UnicodeEncodeError):
        return fallback
    return preferred
