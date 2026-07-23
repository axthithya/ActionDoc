"""Tests for repository-level workflow loading."""

from pathlib import Path

import pytest

from actiondoctor.parser import InvalidRepositoryError, WorkflowLoader
from actiondoctor.parser.loader import MAX_WORKFLOW_BYTES

FIXTURES = Path(__file__).parents[1] / "fixtures" / "repositories"


def test_loads_multiple_workflows() -> None:
    """All discovered valid workflows are parsed in deterministic order."""
    result = WorkflowLoader().load_repository(FIXTURES / "multiple")

    assert result.discovered_file_count == 2
    assert result.successful_count == 2
    assert result.failed_count == 0
    assert [workflow.path.name for workflow in result.workflows] == [
        "a-ci.yml",
        "z-release.yaml",
    ]


def test_partial_success_preserves_errors() -> None:
    """A malformed file does not prevent a valid neighbor from loading."""
    result = WorkflowLoader().load_repository(FIXTURES / "mixed")

    assert result.discovered_file_count == 2
    assert result.successful_count == 1
    assert result.failed_count == 1
    assert result.workflows[0].path.name == "good.yaml"
    assert result.parse_errors[0].file_path.name == "broken.yml"


def test_missing_workflow_directory_is_helpful_result() -> None:
    """Missing workflow directories are represented without an exception."""
    result = WorkflowLoader().load_repository(FIXTURES / "missing_workflows")

    assert result.workflow_directory_exists is False
    assert result.discovered_file_count == 0
    assert result.workflows == []
    assert result.parse_errors == []


def test_empty_workflow_directory_is_helpful_result() -> None:
    """A present directory without YAML files is distinguishable from missing."""
    result = WorkflowLoader().load_repository(FIXTURES / "empty_workflows")

    assert result.workflow_directory_exists is True
    assert result.discovered_file_count == 0


def test_invalid_repository_path_raises_clear_error(tmp_path: Path) -> None:
    """Repository validation happens before discovery."""
    with pytest.raises(InvalidRepositoryError, match="does not exist"):
        WorkflowLoader().load_repository(tmp_path / "missing")


def test_file_path_is_not_a_repository(tmp_path: Path) -> None:
    """A regular file cannot be used as a repository root."""
    path = tmp_path / "file"
    path.write_text("content", encoding="utf-8")

    with pytest.raises(InvalidRepositoryError, match="not a directory"):
        WorkflowLoader().load_repository(path)


def test_invalid_utf8_is_a_per_file_error(tmp_path: Path) -> None:
    """Decoding failures are collected instead of aborting the repository."""
    directory = tmp_path / ".github" / "workflows"
    directory.mkdir(parents=True)
    (directory / "invalid.yml").write_bytes(b"\xff\xfe")

    result = WorkflowLoader().load_repository(tmp_path)

    assert result.discovered_file_count == 1
    assert result.failed_count == 1
    assert "UTF-8" in result.parse_errors[0].error_message


def test_oversized_file_is_a_per_file_error(tmp_path: Path) -> None:
    """The loader applies its documented input-size safety limit."""
    directory = tmp_path / ".github" / "workflows"
    directory.mkdir(parents=True)
    (directory / "large.yml").write_bytes(b"x" * (MAX_WORKFLOW_BYTES + 1))

    result = WorkflowLoader().load_repository(tmp_path)

    assert result.failed_count == 1
    assert "size limit" in result.parse_errors[0].error_message


def test_unreadable_file_does_not_abort_scan(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Operating-system read failures become structured file errors."""
    directory = tmp_path / ".github" / "workflows"
    directory.mkdir(parents=True)
    path = directory / "unreadable.yml"
    path.write_text("name: Unreadable\n", encoding="utf-8")
    original_read_text = Path.read_text

    def raise_for_fixture(
        candidate: Path,
        encoding: str | None = None,
        errors: str | None = None,
    ) -> str:
        if candidate == path:
            raise PermissionError("access denied")
        return original_read_text(candidate, encoding=encoding, errors=errors)

    monkeypatch.setattr(Path, "read_text", raise_for_fixture)

    result = WorkflowLoader().load_repository(tmp_path)

    assert result.failed_count == 1
    assert "access denied" in result.parse_errors[0].error_message
