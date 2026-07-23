"""Rich terminal reporting for complete ActionDoctor scan results."""

from collections import defaultdict
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich.text import Text

from actiondoctor.models import (
    Finding,
    RuleCategory,
    ScanCompleteness,
    ScanResult,
    Severity,
)


class TerminalReporter:
    """Render a readable workflow audit without owning scan policy."""

    def __init__(self, console: Console) -> None:
        self.console = console

    def render(self, result: ScanResult) -> None:
        """Render summary, breakdowns, findings, and operational errors."""
        self.console.print()
        self.console.print("[bold cyan]ActionDoc[/bold cyan]")
        self.console.print("[bold]GitHub Actions Workflow Audit[/bold]")
        self.console.print()
        self._render_summary(result)
        self._render_breakdowns(result)
        self._render_workflows(result)
        self._render_findings(result.findings)
        self._render_errors(result)

    def _render_summary(self, result: ScanResult) -> None:
        self.console.print(
            f"[bold]Repository:[/bold] {result.repository_path or 'unknown'}"
        )
        self.console.print(
            f"[bold]Workflow files discovered:[/bold] {result.workflows_discovered}"
        )
        self.console.print(
            f"[bold]Successfully parsed:[/bold] {result.workflows_parsed}"
        )
        self.console.print(f"[bold]Failed to parse:[/bold] {len(result.parse_errors)}")
        self.console.print(f"[bold]Active rules:[/bold] {result.active_rules}")
        self.console.print(
            f"[bold]Total rules executed:[/bold] {result.rule_evaluations}"
        )
        self.console.print(f"[bold]Total findings:[/bold] {len(result.findings)}")
        self.console.print(
            f"[bold]Rule execution failures:[/bold] {len(result.rule_execution_errors)}"
        )
        self.console.print(f"[bold]Health score:[/bold] {result.health_score}/100")
        self.console.print(f"[bold]Health rating:[/bold] {result.score.rating.value}")
        if result.completeness is ScanCompleteness.COMPLETE:
            status = Text("Complete", style="green")
        else:
            error_count = len(result.parse_errors) + len(result.rule_execution_errors)
            noun = "error" if error_count == 1 else "errors"
            status = Text(f"Incomplete - {error_count} analysis {noun}", style="yellow")
        self.console.print(Text.assemble(("Status: ", "bold"), status))

    def _render_breakdowns(self, result: ScanResult) -> None:
        table = Table(title="Finding summary", show_header=True)
        table.add_column("Dimension")
        table.add_column("Counts")
        categories = ", ".join(
            f"{category.value}: {result.score.finding_count_by_category[category]}"
            for category in RuleCategory
        )
        severities = ", ".join(
            f"{severity.value}: {result.score.finding_count_by_severity[severity]}"
            for severity in reversed(Severity)
        )
        table.add_row("Category", categories)
        table.add_row("Severity", severities)
        self.console.print()
        self.console.print(table)

    def _render_workflows(self, result: ScanResult) -> None:
        if not result.workflow_directory_exists:
            self.console.print()
            self.console.print(
                "No .github/workflows directory was found. "
                "There are no workflows to analyze."
            )
            return
        if result.workflows_discovered == 0:
            self.console.print()
            self.console.print(
                "The .github/workflows directory contains no .yml or .yaml files."
            )
            return
        if result.scanned_files:
            self.console.print()
            self.console.print("[bold]Parsed workflows[/bold]")
            for path in result.scanned_files:
                self.console.print(Text.assemble(("  [OK] ", "green"), path.as_posix()))

    def _render_findings(self, findings: list[Finding]) -> None:
        if not findings:
            return
        grouped: defaultdict[str, list[Finding]] = defaultdict(list)
        for finding in findings:
            grouped[finding.file_path.as_posix()].append(finding)
        self.console.print()
        self.console.print("[bold]Findings[/bold]")
        for workflow_path in sorted(grouped, key=str.casefold):
            self.console.print()
            self.console.print(Text(workflow_path, style="bold"))
            for finding in grouped[workflow_path]:
                self.console.print(
                    Text.assemble(
                        "  ",
                        (f"[{finding.severity.value.upper()}] ", "yellow"),
                        (finding.rule_id, "cyan"),
                        f" - {finding.title}",
                    )
                )
                context = self._finding_context(finding)
                if context:
                    self.console.print(f"    Location: {'; '.join(context)}")
                self.console.print(f"    Description: {finding.description}")
                if finding.remediation:
                    self.console.print(f"    Remediation: {finding.remediation}")

    def _render_errors(self, result: ScanResult) -> None:
        if result.parse_errors:
            self.console.print()
            self.console.print("[bold red]Workflow parse errors[/bold red]")
            for parse_error in result.parse_errors:
                message = parse_error.error_message
                if parse_error.line is not None:
                    message += f" at line {parse_error.line}"
                    if parse_error.column is not None:
                        message += f", column {parse_error.column}"
                display_path = self._display_path(parse_error.file_path, result)
                self.console.print(f"  {display_path} - {message}")
        if result.rule_execution_errors:
            self.console.print()
            self.console.print("[bold red]Rule execution errors[/bold red]")
            for execution_error in result.rule_execution_errors:
                self.console.print(
                    f"  {execution_error.workflow_path}: {execution_error.rule_id} "
                    f"failed with {execution_error.error_type} - "
                    f"{execution_error.error_message}"
                )

    @staticmethod
    def _finding_context(finding: Finding) -> list[str]:
        context: list[str] = []
        if finding.line is not None:
            location = f"line {finding.line}"
            if finding.column is not None:
                location += f", column {finding.column}"
            context.append(location)
        if finding.job_id:
            context.append(f"job {finding.job_id}")
        if finding.yaml_path:
            context.append(finding.yaml_path)
        return context

    @staticmethod
    def _display_path(path: Path, result: ScanResult) -> str:
        if result.repository_path is not None:
            try:
                return path.relative_to(result.repository_path).as_posix()
            except ValueError:
                pass
        return path.as_posix()
