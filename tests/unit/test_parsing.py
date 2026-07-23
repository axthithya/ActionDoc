"""Tests for safe GitHub Actions YAML parsing."""

from pathlib import Path

from actiondoctor.models import WorkflowFile, WorkflowParseError
from actiondoctor.parser import WorkflowParser

FIXTURES = Path(__file__).parents[1] / "fixtures" / "repositories"


def parse_fixture(repository: str, filename: str) -> WorkflowFile | WorkflowParseError:
    """Parse a fixture file through the public parser contract."""
    path = FIXTURES / repository / ".github" / "workflows" / filename
    return WorkflowParser().parse(
        path=path,
        relative_path=f".github/workflows/{filename}",
        raw_text=path.read_text(encoding="utf-8"),
    )


def test_parses_basic_workflow_and_captures_source() -> None:
    """A valid mapping retains source identity and raw text."""
    result = parse_fixture("valid_basic", "ci.yml")

    assert isinstance(result, WorkflowFile)
    assert result.path.name == "ci.yml"
    assert result.relative_path == ".github/workflows/ci.yml"
    assert result.parsed_content["name"] == "CI"
    assert "jobs" in result.parsed_content
    assert result.raw_text.startswith("name: CI")


def test_preserves_on_as_a_string_key() -> None:
    """YAML 1.2 semantics prevent `on` from becoming boolean true."""
    result = parse_fixture("valid_on", "events.yml")

    assert isinstance(result, WorkflowFile)
    assert "on" in result.parsed_content
    assert "True" not in result.parsed_content
    assert isinstance(result.parsed_content["on"], dict)


def test_parses_matrix_workflow() -> None:
    """Nested matrix structures remain available to future rules."""
    result = parse_fixture("matrix", "matrix.yaml")

    assert isinstance(result, WorkflowFile)
    jobs = result.parsed_content["jobs"]
    assert jobs["test"]["strategy"]["matrix"]["python-version"] == [
        "3.12",
        "3.13",
    ]


def test_empty_file_returns_structured_error() -> None:
    """An empty YAML document is not accepted as a workflow."""
    result = parse_fixture("empty", "empty.yml")

    assert isinstance(result, WorkflowParseError)
    assert result.error_message == "Workflow file is empty"
    assert result.line is None
    assert result.column is None


def test_invalid_yaml_includes_one_based_location() -> None:
    """Syntax errors report useful, user-facing source coordinates."""
    result = parse_fixture("invalid", "broken.yml")

    assert isinstance(result, WorkflowParseError)
    assert result.error_message.startswith("Invalid YAML:")
    assert result.line is not None and result.line >= 1
    assert result.column is not None and result.column >= 1


def test_top_level_list_returns_structured_error() -> None:
    """Only top-level mappings can represent GitHub Actions workflows."""
    result = parse_fixture("top_level_list", "list.yml")

    assert isinstance(result, WorkflowParseError)
    assert result.error_message == "Top-level YAML value must be a mapping"


def test_multiple_yaml_documents_are_rejected(tmp_path: Path) -> None:
    """A workflow file must contain exactly one YAML document."""
    path = tmp_path / "multiple.yml"
    raw_text = "name: First\n---\nname: Second\n"

    result = WorkflowParser().parse(
        path=path,
        relative_path=".github/workflows/multiple.yml",
        raw_text=raw_text,
    )

    assert isinstance(result, WorkflowParseError)
    assert result.error_message.startswith("Invalid YAML:")
