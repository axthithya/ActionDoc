"""Tests for workflow file discovery."""

from pathlib import Path

from actiondoctor.parser.discovery import discover_workflow_files

FIXTURES = Path(__file__).parents[1] / "fixtures" / "repositories"


def test_discovers_yml_and_yaml_in_deterministic_order() -> None:
    """Both supported extensions are returned in stable name order."""
    discovered = discover_workflow_files(FIXTURES / "multiple")

    assert [path.name for path in discovered] == ["a-ci.yml", "z-release.yaml"]


def test_ignores_unsupported_files_and_directories() -> None:
    """Only regular workflow files directly in the workflow directory count."""
    discovered = discover_workflow_files(FIXTURES / "multiple")

    assert all(path.suffix in {".yml", ".yaml"} for path in discovered)
    assert not any(path.name == "ignored.yml" for path in discovered)


def test_supports_case_insensitive_extensions(tmp_path: Path) -> None:
    """Extension matching behaves consistently on case-sensitive systems."""
    directory = tmp_path / ".github" / "workflows"
    directory.mkdir(parents=True)
    (directory / "UPPER.YML").write_text("name: Upper\n", encoding="utf-8")

    discovered = discover_workflow_files(tmp_path)

    assert [path.name for path in discovered] == ["UPPER.YML"]


def test_missing_workflow_directory_returns_empty_list() -> None:
    """A repository without the conventional directory is not an exception."""
    assert discover_workflow_files(FIXTURES / "missing_workflows") == []
