"""Finding model."""

from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from actiondoctor.models.enums import RuleCategory, Severity

RULE_ID_PATTERN = r"^(?:SEC|COST|REL|MAINT)(?:00[1-9]|0[1-9][0-9]|[1-9][0-9]{2})$"
RuleId = Annotated[str, Field(pattern=RULE_ID_PATTERN)]


class Finding(BaseModel):
    """One problem identified in a workflow."""

    model_config = ConfigDict(frozen=True)

    rule_id: RuleId
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    severity: Severity
    category: RuleCategory
    file_path: Path
    line: int | None = Field(default=None, ge=1)
    column: int | None = Field(default=None, ge=1)
    job_id: str | None = Field(default=None, min_length=1)
    yaml_path: str | None = Field(default=None, min_length=1)
    remediation: str | None = Field(default=None, min_length=1)
    documentation_url: str | None = Field(default=None, min_length=1)
