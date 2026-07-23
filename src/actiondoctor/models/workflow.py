"""Models for discovered and parsed GitHub Actions workflows."""

from pathlib import Path
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class YamlLocation(BaseModel):
    """One-based source position for a parsed YAML path."""

    model_config = ConfigDict(frozen=True)

    line: int = Field(ge=1)
    column: int = Field(ge=1)


class WorkflowFile(BaseModel):
    """A successfully loaded and parsed workflow file."""

    model_config = ConfigDict(frozen=True)

    path: Path
    relative_path: str = Field(min_length=1)
    raw_text: str
    parsed_content: dict[str, Any]
    source_locations: dict[str, YamlLocation] = Field(default_factory=dict)

    def location_for(self, yaml_path: str) -> YamlLocation | None:
        """Return a source position when the parser captured one."""
        return self.source_locations.get(yaml_path)


class WorkflowParseError(BaseModel):
    """A structured loading or parsing failure for one workflow."""

    model_config = ConfigDict(frozen=True)

    file_path: Path
    error_message: str = Field(min_length=1)
    line: int | None = Field(default=None, ge=1)
    column: int | None = Field(default=None, ge=1)


class WorkflowLoadResult(BaseModel):
    """Outcome of discovering, loading, and parsing a repository's workflows."""

    model_config = ConfigDict(frozen=True)

    repository_path: Path
    workflow_directory: Path
    workflow_directory_exists: bool
    workflows: list[WorkflowFile] = Field(default_factory=list)
    parse_errors: list[WorkflowParseError] = Field(default_factory=list)
    discovered_file_count: int = Field(ge=0)

    @model_validator(mode="after")
    def outcomes_match_discovered_count(self) -> Self:
        """Require one success or failure for every discovered file."""
        outcomes = len(self.workflows) + len(self.parse_errors)
        if outcomes != self.discovered_file_count:
            msg = "discovered_file_count must match workflow and error outcomes"
            raise ValueError(msg)
        return self

    @property
    def successful_count(self) -> int:
        """Number of workflows parsed successfully."""
        return len(self.workflows)

    @property
    def failed_count(self) -> int:
        """Number of workflows that could not be loaded or parsed."""
        return len(self.parse_errors)
