"""Models produced by rule-engine execution."""

from pydantic import BaseModel, ConfigDict, Field

from actiondoctor.models.finding import Finding, RuleId


class RuleExecutionError(BaseModel):
    """Safe diagnostic for an unexpected rule exception."""

    model_config = ConfigDict(frozen=True)

    rule_id: RuleId
    workflow_path: str = Field(min_length=1)
    error_type: str = Field(min_length=1)
    error_message: str = Field(min_length=1)


class RuleEngineResult(BaseModel):
    """Deterministic output from evaluating rules against workflows."""

    model_config = ConfigDict(frozen=True)

    findings: list[Finding] = Field(default_factory=list)
    execution_errors: list[RuleExecutionError] = Field(default_factory=list)
    rules_executed: int = Field(ge=0)
