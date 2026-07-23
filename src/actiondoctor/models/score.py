"""Typed health-score result models."""

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from actiondoctor.models.enums import (
    HealthRating,
    RuleCategory,
    ScanCompleteness,
    Severity,
)


class ScoreResult(BaseModel):
    """Explainable deterministic score and its complete breakdown."""

    model_config = ConfigDict(frozen=True)

    starting_score: int = Field(default=100, ge=0, le=100)
    raw_penalty: int = Field(ge=0)
    capped_penalty: int = Field(ge=0)
    final_score: int = Field(ge=0, le=100)
    rating: HealthRating
    penalty_by_severity: dict[Severity, int]
    penalty_by_rule_id: dict[str, int]
    finding_count_by_severity: dict[Severity, int]
    finding_count_by_category: dict[RuleCategory, int]
    completeness: ScanCompleteness

    @model_validator(mode="after")
    def validate_score_relationships(self) -> Self:
        """Keep the public score breakdown internally consistent."""
        if self.capped_penalty > self.raw_penalty:
            raise ValueError("capped_penalty cannot exceed raw_penalty")
        expected_score = max(0, self.starting_score - self.capped_penalty)
        if self.final_score != expected_score:
            raise ValueError("final_score does not match the capped penalty")
        return self
