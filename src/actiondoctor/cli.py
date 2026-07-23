"""Command-line interface for ActionDoctor."""

import typer
from rich.console import Console

from actiondoctor import __version__

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
def scan() -> None:
    """Show the scanner foundation status."""
    console.print(
        "ActionDoctor scanner foundation is ready. "
        "Workflow analysis is not implemented yet.",
        soft_wrap=True,
    )
