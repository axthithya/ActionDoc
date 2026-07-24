"""Explicit versioned models for the public JSON report contract."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from actiondoctor.models.enums import (
    HealthRating,
    RuleCategory,
    ScanCompleteness,
    Severity,
)

REPORT_SCHEMA_VERSION: Literal["1.0"] = "1.0"


class ReportFinding(BaseModel):
    """Stable public representation of one rule finding."""

    model_config = ConfigDict(frozen=True)

    rule_id: str
    title: str
    description: str
    severity: Severity
    category: RuleCategory
    file: str
    line: int | None
    column: int | None
    job_id: str | None
    step_index: int | None
    step_name: str | None
    yaml_path: str | None
    remediation: str | None
    documentation_url: str | None


class ReportParseError(BaseModel):
    """Stable public representation of a workflow parsing failure."""

    model_config = ConfigDict(frozen=True)

    file: str
    message: str
    line: int | None
    column: int | None


class ReportRuleExecutionError(BaseModel):
    """Safe public representation of an isolated rule failure."""

    model_config = ConfigDict(frozen=True)

    rule_id: str
    file: str
    error_type: str
    message: str


class JsonReportDocument(BaseModel):
    """Version 1.0 JSON report document."""

    model_config = ConfigDict(frozen=True)

    schema_version: Literal["1.0"] = REPORT_SCHEMA_VERSION
    actiondoctor_version: str
    repository: str
    completeness: ScanCompleteness
    workflows_discovered: int
    workflows_parsed: int
    active_rule_count: int
    rule_workflow_evaluation_count: int
    finding_count: int
    parse_error_count: int
    rule_execution_error_count: int
    starting_score: int
    health_score: int
    health_rating: HealthRating
    raw_penalty: int
    capped_penalty: int
    severity_summary: dict[Severity, int]
    category_summary: dict[RuleCategory, int]
    penalty_by_severity: dict[Severity, int]
    penalty_by_rule_id: dict[str, int]
    findings: list[ReportFinding]
    parse_errors: list[ReportParseError]
    rule_execution_errors: list[ReportRuleExecutionError]
