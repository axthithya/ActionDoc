"""Repository-level workflow loading."""

from pathlib import Path

from actiondoctor.models import WorkflowLoadResult, WorkflowParseError
from actiondoctor.parser.discovery import (
    discover_workflow_files,
    workflow_directory,
)
from actiondoctor.parser.yaml_parser import WorkflowParser

MAX_WORKFLOW_BYTES = 1_000_000


class InvalidRepositoryError(ValueError):
    """Raised when the requested repository path is not a directory."""


class WorkflowLoader:
    """Discover, read, and parse all workflows in a repository."""

    def __init__(self, parser: WorkflowParser | None = None) -> None:
        self._parser = parser or WorkflowParser()

    def load_repository(self, repository_path: Path) -> WorkflowLoadResult:
        """Load all supported workflows without aborting on per-file errors."""
        repository = repository_path.expanduser().resolve()
        if not repository.exists():
            raise InvalidRepositoryError(
                f"Repository path does not exist: {repository_path}"
            )
        if not repository.is_dir():
            raise InvalidRepositoryError(
                f"Repository path is not a directory: {repository_path}"
            )

        directory = workflow_directory(repository)
        directory_exists = directory.is_dir()
        discovered = discover_workflow_files(repository)
        workflows = []
        errors = []

        for path in discovered:
            relative_path = path.relative_to(repository).as_posix()
            try:
                if path.stat().st_size > MAX_WORKFLOW_BYTES:
                    errors.append(
                        WorkflowParseError(
                            file_path=path,
                            error_message=(
                                "Workflow file exceeds the 1,000,000-byte size limit"
                            ),
                        )
                    )
                    continue
                raw_text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeError) as error:
                errors.append(
                    WorkflowParseError(
                        file_path=path,
                        error_message=f"Unable to read workflow as UTF-8: {error}",
                    )
                )
                continue

            outcome = self._parser.parse(
                path=path,
                relative_path=relative_path,
                raw_text=raw_text,
            )
            if isinstance(outcome, WorkflowParseError):
                errors.append(outcome)
            else:
                workflows.append(outcome)

        return WorkflowLoadResult(
            repository_path=repository,
            workflow_directory=directory,
            workflow_directory_exists=directory_exists,
            workflows=workflows,
            parse_errors=errors,
            discovered_file_count=len(discovered),
        )
