"""Command-line interface for ActionDoctor."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.text import Text

from actiondoctor import __version__
from actiondoctor.models import WorkflowLoadResult
from actiondoctor.parser import InvalidRepositoryError, WorkflowLoader

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
        _render_scan_result(result)
    except InvalidRepositoryError as error:
        console.print(Text(f"Error: {error}", style="bold red"))
        raise typer.Exit(code=2) from error
    except Exception as error:
        console.print(Text(f"Unexpected error: {error}", style="bold red"))
        raise typer.Exit(code=2) from error

    if result.parse_errors:
        raise typer.Exit(code=1)


def _render_scan_result(result: WorkflowLoadResult) -> None:
    """Render the phase-two terminal scan summary."""
    console.print()
    console.print("[bold]ActionDoctor Scan[/bold]")
    console.print()
    console.print(Text(f"Repository: {result.repository_path}"))
    console.print(f"Workflow files discovered: {result.discovered_file_count}")
    console.print(f"Successfully parsed: {result.successful_count}")
    console.print(f"Failed to parse: {result.failed_count}")
    console.print()

    if not result.workflow_directory_exists:
        console.print(
            "No .github/workflows directory was found. There are no workflows to parse."
        )
        return
    if result.discovered_file_count == 0:
        console.print(
            "The .github/workflows directory contains no .yml or .yaml files."
        )
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


def _terminal_marker(preferred: str, fallback: str) -> str:
    """Return a status marker supported by the active terminal encoding."""
    encoding = getattr(console.file, "encoding", None) or "utf-8"
    try:
        preferred.encode(encoding)
    except (LookupError, UnicodeEncodeError):
        return fallback
    return preferred
