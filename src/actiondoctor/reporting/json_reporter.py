"""Deterministic JSON report generation."""

import json

from actiondoctor import __version__
from actiondoctor.models import (
    JsonReportDocument,
    ReportFinding,
    ReportParseError,
    ReportRuleExecutionError,
    ScanResult,
)
from actiondoctor.reporting.common import (
    portable_path,
    repository_path,
    sorted_execution_errors,
    sorted_findings,
    sorted_parse_errors,
    step_index,
)


class JsonReporter:
    """Project a scan result into the stable JSON schema."""

    def render(self, result: ScanResult) -> str:
        """Return an indented UTF-8 JSON document with a trailing newline."""
        document = self.document(result)
        payload = document.model_dump(mode="json")
        return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"

    def document(self, result: ScanResult) -> JsonReportDocument:
        """Build the typed public document without exposing internal models."""
        findings = [
            ReportFinding(
                rule_id=finding.rule_id,
                title=finding.title,
                description=finding.description,
                severity=finding.severity,
                category=finding.category,
                file=portable_path(finding.file_path, result),
                line=finding.line,
                column=finding.column,
                job_id=finding.job_id,
                step_index=step_index(finding.yaml_path),
                step_name=None,
                yaml_path=finding.yaml_path,
                remediation=finding.remediation,
                documentation_url=finding.documentation_url,
            )
            for finding in sorted_findings(result)
        ]
        parse_errors = [
            ReportParseError(
                file=portable_path(error.file_path, result),
                message=error.error_message,
                line=error.line,
                column=error.column,
            )
            for error in sorted_parse_errors(result)
        ]
        execution_errors = [
            ReportRuleExecutionError(
                rule_id=error.rule_id,
                file=portable_path(error.workflow_path, result),
                error_type=error.error_type,
                message=error.error_message,
            )
            for error in sorted_execution_errors(result)
        ]
        return JsonReportDocument(
            actiondoctor_version=__version__,
            repository=repository_path(result),
            completeness=result.completeness,
            workflows_discovered=result.workflows_discovered,
            workflows_parsed=result.workflows_parsed,
            active_rule_count=result.active_rules,
            rule_workflow_evaluation_count=result.rule_evaluations,
            finding_count=len(findings),
            parse_error_count=len(parse_errors),
            rule_execution_error_count=len(execution_errors),
            starting_score=result.score.starting_score,
            health_score=result.score.final_score,
            health_rating=result.score.rating,
            raw_penalty=result.score.raw_penalty,
            capped_penalty=result.score.capped_penalty,
            severity_summary=result.score.finding_count_by_severity,
            category_summary=result.score.finding_count_by_category,
            penalty_by_severity=result.score.penalty_by_severity,
            penalty_by_rule_id=dict(sorted(result.score.penalty_by_rule_id.items())),
            findings=findings,
            parse_errors=parse_errors,
            rule_execution_errors=execution_errors,
        )
