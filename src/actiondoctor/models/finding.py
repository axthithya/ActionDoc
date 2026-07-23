"""Finding model."""

from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from actiondoctor.models.enums import RuleCategory, Severity

RuleId = Annotated[str, Field(pattern=r"^(?:SEC|COST|REL|MAINT)\d{3}$")]


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
    remediation: str | None = Field(default=None, min_length=1)
