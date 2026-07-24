"""Thin composite-action bridge to the installed ActionDoc CLI."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

VALID_FAIL_ON = frozenset({"critical", "high", "medium", "low", "never"})
VALID_REPORT_FORMATS = frozenset({"markdown", "json", "none"})


class ActionInputError(ValueError):
    """Raised when a composite-action input is invalid."""


@dataclass(frozen=True)
class ActionConfig:
    """Validated action inputs and the selected report destination."""

    repository_path: str
    fail_on: str
    report_format: str
    report_path: Path | None


run_command = subprocess.run


def load_config(environment: Mapping[str, str]) -> ActionConfig:
    """Validate explicit action environment values without shell evaluation."""
    repository_path = environment.get("ACTIONDOC_PATH", ".").strip()
    fail_on = environment.get("ACTIONDOC_FAIL_ON", "high").strip().lower()
    report_format = (
        environment.get("ACTIONDOC_REPORT_FORMAT", "markdown").strip().lower()
    )
    requested_path = environment.get("ACTIONDOC_REPORT_PATH", "").strip()

    if not repository_path:
        raise ActionInputError("path must not be empty")
    if fail_on not in VALID_FAIL_ON:
        valid = ", ".join(sorted(VALID_FAIL_ON))
        raise ActionInputError(f"fail-on must be one of: {valid}")
    if report_format not in VALID_REPORT_FORMATS:
        valid = ", ".join(sorted(VALID_REPORT_FORMATS))
        raise ActionInputError(f"report-format must be one of: {valid}")
    if "\x00" in requested_path or "\n" in requested_path or "\r" in requested_path:
        raise ActionInputError("report-path must be a single valid path")
    if report_format == "none":
        if requested_path:
            raise ActionInputError(
                "report-path cannot be set when report-format is none"
            )
        return ActionConfig(repository_path, fail_on, report_format, None)

    if requested_path:
        report_path = Path(requested_path)
    else:
        runner_temp = Path(environment.get("RUNNER_TEMP", tempfile.gettempdir()))
        extension = "md" if report_format == "markdown" else "json"
        report_path = runner_temp / f"actiondoc-report.{extension}"
    return ActionConfig(repository_path, fail_on, report_format, report_path)


def write_action_output(
    environment: Mapping[str, str], report_path: Path | None
) -> None:
    """Set the composite output when GitHub supplied an output-file path."""
    output_file = environment.get("GITHUB_OUTPUT")
    if not output_file:
        return
    value = "" if report_path is None else str(report_path)
    with Path(output_file).open("a", encoding="utf-8", newline="") as output:
        output.write(f"report-path={value}\n")


def append_markdown_summary(environment: Mapping[str, str], report_path: Path) -> None:
    """Append the completed Markdown report when a step-summary file exists."""
    summary_file = environment.get("GITHUB_STEP_SUMMARY")
    if not summary_file:
        return
    report = report_path.read_text(encoding="utf-8")
    with Path(summary_file).open("a", encoding="utf-8", newline="") as summary:
        summary.write(report)
        if not report.endswith("\n"):
            summary.write("\n")


def execute(
    config: ActionConfig,
    environment: Mapping[str, str],
    action_root: Path,
) -> int:
    """Install this checked-out source and propagate the existing CLI exit code."""
    write_action_output(environment, None)
    install = run_command(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--quiet",
            str(action_root),
        ],
        check=False,
    )
    if install.returncode != 0:
        return install.returncode

    command = [
        sys.executable,
        "-m",
        "actiondoctor",
        "scan",
        config.repository_path,
        "--fail-on",
        config.fail_on,
    ]
    if config.report_format == "none":
        command.extend(["--format", "terminal"])
    else:
        assert config.report_path is not None
        command.extend(
            ["--format", config.report_format, "--output", str(config.report_path)]
        )
    scan = run_command(command, check=False)

    if config.report_path is not None and config.report_path.is_file():
        write_action_output(environment, config.report_path)
        if config.report_format == "markdown":
            append_markdown_summary(environment, config.report_path)
    return scan.returncode


def main() -> int:
    """Run the action without exposing a traceback for invalid inputs."""
    try:
        config = load_config(os.environ)
    except ActionInputError as error:
        print(f"ActionDoc action input error: {error}", file=sys.stderr)
        return 2
    action_root = Path(__file__).resolve().parents[1]
    return execute(config, os.environ, action_root)


if __name__ == "__main__":
    raise SystemExit(main())
