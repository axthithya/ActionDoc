"""Safe YAML parsing for GitHub Actions workflows."""

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.error import MarkedYAMLError, YAMLError

from actiondoctor.models import WorkflowFile, WorkflowParseError


class WorkflowParser:
    """Parse one workflow using YAML 1.2 round-trip semantics."""

    def parse(
        self,
        *,
        path: Path,
        relative_path: str,
        raw_text: str,
    ) -> WorkflowFile | WorkflowParseError:
        """Return a parsed workflow or a structured parsing failure."""
        parser = YAML(typ="rt", pure=True)
        parser.version = (1, 2)
        parser.allow_duplicate_keys = False

        try:
            parsed = parser.load(raw_text)
        except MarkedYAMLError as error:
            return self._marked_error(path, error)
        except YAMLError as error:
            return WorkflowParseError(
                file_path=path,
                error_message=f"Invalid YAML: {self._first_line(error)}",
            )

        if parsed is None:
            return WorkflowParseError(
                file_path=path,
                error_message="Workflow file is empty",
            )
        if not isinstance(parsed, Mapping):
            return WorkflowParseError(
                file_path=path,
                error_message="Top-level YAML value must be a mapping",
            )

        return WorkflowFile(
            path=path,
            relative_path=relative_path,
            raw_text=raw_text,
            parsed_content=self._to_serializable_content(parsed),
        )

    @staticmethod
    def _marked_error(
        path: Path,
        error: MarkedYAMLError,
    ) -> WorkflowParseError:
        problem = error.problem or WorkflowParser._first_line(error)
        mark = error.problem_mark
        return WorkflowParseError(
            file_path=path,
            error_message=f"Invalid YAML: {problem}",
            line=mark.line + 1 if mark is not None else None,
            column=mark.column + 1 if mark is not None else None,
        )

    @staticmethod
    def _first_line(error: Exception) -> str:
        text = str(error).strip()
        return text.splitlines()[0] if text else type(error).__name__

    @staticmethod
    def _to_serializable_content(value: Any) -> Any:
        """Convert round-trip YAML containers to serializable containers."""
        if isinstance(value, Mapping):
            return {
                str(key): WorkflowParser._to_serializable_content(item)
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [WorkflowParser._to_serializable_content(item) for item in value]
        return value
