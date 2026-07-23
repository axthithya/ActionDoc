"""Scan result model."""

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, computed_field

from actiondoctor.models.enums import ScanCompleteness, ScanStatus
from actiondoctor.models.finding import Finding
from actiondoctor.models.rule import RuleExecutionError
from actiondoctor.models.score import ScoreResult
from actiondoctor.models.workflow import WorkflowParseError
from actiondoctor.scoring import clean_score_result


class ScanResult(BaseModel):
    """Validated result produced by a completed or partial scan."""

    model_config = ConfigDict(frozen=True)

    repository_path: Path | None = None
    workflow_directory_exists: bool = True
    workflows_discovered: int = Field(default=0, ge=0)
    workflows_parsed: int = Field(default=0, ge=0)
    scanned_files: list[Path] = Field(default_factory=list)
    parse_errors: list[WorkflowParseError] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    rule_execution_errors: list[RuleExecutionError] = Field(default_factory=list)
    active_rules: int = Field(default=0, ge=0)
    rule_evaluations: int = Field(default=0, ge=0)
    score: ScoreResult = Field(default_factory=clean_score_result)
    status: ScanStatus = ScanStatus.SUCCESS

    @computed_field  # type: ignore[prop-decorator]
    @property
    def health_score(self) -> int:
        """Compatibility projection of the structured score."""
        return self.score.final_score

    @computed_field  # type: ignore[prop-decorator]
    @property
    def completeness(self) -> ScanCompleteness:
        """Expose score completeness directly on the scan result."""
        return self.score.completeness
