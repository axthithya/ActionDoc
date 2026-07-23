"""Scan result model."""

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from actiondoctor.models.enums import ScanStatus
from actiondoctor.models.finding import Finding


class ScanResult(BaseModel):
    """Validated result produced by a completed or partial scan."""

    model_config = ConfigDict(frozen=True)

    scanned_files: list[Path] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    health_score: int = Field(default=100, ge=0, le=100)
    status: ScanStatus = ScanStatus.SUCCESS
