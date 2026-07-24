"""Standalone deterministic Markdown report generation."""

import re
from collections import defaultdict

from actiondoctor.models import (
    Finding,
    RuleCategory,
    ScanCompleteness,
    ScanResult,
    Severity,
)
from actiondoctor.reporting.common import (
    portable_path,
    repository_path,
    sorted_execution_errors,
    sorted_findings,
    sorted_parse_errors,
    step_index,
)

MARKDOWN_SPECIAL = re.compile(r"([\\`*_[\]{}()#+!|>])")


def escape_markdown(value: object) -> str:
    """Escape user-controlled text for headings and compact bullet values."""
    normalized = " ".join(str(value).splitlines())
    return MARKDOWN_SPECIAL.sub(r"\\\1", normalized)


class MarkdownReporter:
    """Project a scan result into a standalone Markdown report."""

    def render(self, result: ScanResult) -> str:
        """Return deterministic Markdown with a trailing newline."""
        lines = ["# ActionDoc Report", "", "## Summary", ""]
        if result.completeness is ScanCompleteness.INCOMPLETE:
            error_count = len(result.parse_errors) + len(result.rule_execution_errors)
            noun = "error" if error_count == 1 else "errors"
            lines.extend(
                [
                    f"> **Warning:** Incomplete analysis ({error_count} {noun}).",
                    "",
                ]
            )
        lines.extend(
            [
                f"- **Repository:** {escape_markdown(repository_path(result))}",
                f"- **Health score:** {result.health_score}/100",
                f"- **Health rating:** {escape_markdown(result.score.rating.value)}",
                f"- **Completeness:** {result.completeness.value}",
                f"- **Workflows discovered:** {result.workflows_discovered}",
                f"- **Workflows parsed:** {result.workflows_parsed}",
                f"- **Parse failures:** {len(result.parse_errors)}",
                f"- **Active rules:** {result.active_rules}",
                f"- **Rule/workflow evaluations:** {result.rule_evaluations}",
                f"- **Total findings:** {len(result.findings)}",
                "",
                "## Severity Summary",
                "",
                "| Severity | Count |",
                "|---|---:|",
            ]
        )
        for severity in reversed(Severity):
            lines.append(
                f"| {severity.value.title()} | "
                f"{result.score.finding_count_by_severity[severity]} |"
            )
        lines.extend(
            [
                "",
                "## Category Summary",
                "",
                "| Category | Count |",
                "|---|---:|",
            ]
        )
        for category in RuleCategory:
            lines.append(
                f"| {category.value.title()} | "
                f"{result.score.finding_count_by_category[category]} |"
            )
        lines.extend(["", "## Findings", ""])
        findings = sorted_findings(result)
        if not findings:
            lines.extend(["No findings were detected.", ""])
        else:
            grouped: defaultdict[str, list[Finding]] = defaultdict(list)
            for finding in findings:
                grouped[portable_path(finding.file_path, result)].append(finding)
            for path in sorted(grouped, key=lambda value: (value.casefold(), value)):
                lines.extend([f"### {escape_markdown(path)}", ""])
                for finding in grouped[path]:
                    lines.append(
                        f"#### {finding.severity.value.upper()} "
                        f"`{finding.rule_id}` - {escape_markdown(finding.title)}"
                    )
                    lines.append("")
                    location = path
                    if finding.line is not None:
                        location += f":{finding.line}"
                        if finding.column is not None:
                            location += f":{finding.column}"
                    lines.append(f"- **Location:** {escape_markdown(location)}")
                    if finding.job_id is not None:
                        lines.append(f"- **Job:** {escape_markdown(finding.job_id)}")
                    index = step_index(finding.yaml_path)
                    if index is not None:
                        lines.append(f"- **Step index:** {index}")
                    if finding.yaml_path is not None:
                        lines.append(
                            f"- **YAML path:** {escape_markdown(finding.yaml_path)}"
                        )
                    lines.append(
                        f"- **Description:** {escape_markdown(finding.description)}"
                    )
                    if finding.remediation is not None:
                        lines.append(
                            f"- **Remediation:** {escape_markdown(finding.remediation)}"
                        )
                    lines.append("")
        self._append_errors(lines, result)
        return "\n".join(lines).rstrip() + "\n"

    @staticmethod
    def _append_errors(lines: list[str], result: ScanResult) -> None:
        lines.extend(["## Parse Errors", ""])
        parse_errors = sorted_parse_errors(result)
        if not parse_errors:
            lines.extend(["None.", ""])
        else:
            for parse_error in parse_errors:
                path = portable_path(parse_error.file_path, result)
                location = path
                if parse_error.line is not None:
                    location += f":{parse_error.line}"
                    if parse_error.column is not None:
                        location += f":{parse_error.column}"
                lines.append(
                    f"- **{escape_markdown(location)}:** "
                    f"{escape_markdown(parse_error.error_message)}"
                )
            lines.append("")
        lines.extend(["## Rule Execution Errors", ""])
        execution_errors = sorted_execution_errors(result)
        if not execution_errors:
            lines.append("None.")
        else:
            for execution_error in execution_errors:
                path = portable_path(execution_error.workflow_path, result)
                lines.append(
                    f"- **{escape_markdown(execution_error.rule_id)}** in "
                    f"{escape_markdown(path)} "
                    f"({escape_markdown(execution_error.error_type)}): "
                    f"{escape_markdown(execution_error.error_message)}"
                )
