"""Tests for the reusable GitHub Action contract and entry point."""

from dataclasses import dataclass
from pathlib import Path

import pytest
from ruamel.yaml import YAML
from scripts import github_action_entrypoint as entrypoint

ROOT = Path(__file__).resolve().parents[2]


@dataclass
class CompletedCommand:
    """Minimal subprocess result used by the action-entry-point tests."""

    returncode: int


class FakeCommandRunner:
    """Record argument lists and create reports only after simulated scans."""

    def __init__(self, scan_returncode: int = 0) -> None:
        self.calls: list[list[str]] = []
        self.scan_returncode = scan_returncode

    def __call__(self, command: list[str], *, check: bool) -> CompletedCommand:
        assert check is False
        self.calls.append(command)
        if "scan" in command:
            if "--output" in command and self.scan_returncode in {0, 1}:
                report_path = Path(command[command.index("--output") + 1])
                report_path.parent.mkdir(parents=True, exist_ok=True)
                report_path.write_text("# ActionDoc Report\n", encoding="utf-8")
            return CompletedCommand(self.scan_returncode)
        return CompletedCommand(0)


def action_environment(tmp_path: Path, **overrides: str) -> dict[str, str]:
    """Create representative explicit composite-action input files."""
    output = tmp_path / "github-output"
    summary = tmp_path / "github-summary"
    output.touch()
    summary.touch()
    environment = {
        "ACTIONDOC_PATH": ".",
        "ACTIONDOC_FAIL_ON": "high",
        "ACTIONDOC_REPORT_FORMAT": "markdown",
        "ACTIONDOC_REPORT_PATH": "",
        "RUNNER_TEMP": str(tmp_path / "runner temp"),
        "GITHUB_OUTPUT": str(output),
        "GITHUB_STEP_SUMMARY": str(summary),
    }
    environment.update(overrides)
    return environment


def test_action_metadata_declares_required_inputs_outputs_and_defaults() -> None:
    """The Marketplace metadata is parseable and exposes the public contract."""
    yaml = YAML(typ="safe")
    metadata = yaml.load((ROOT / "action.yml").read_text(encoding="utf-8"))

    assert metadata["name"] == "ActionDoc"
    assert metadata["runs"]["using"] == "composite"
    assert metadata["branding"] == {"icon": "shield", "color": "blue"}
    assert metadata["inputs"]["path"]["default"] == "."
    assert metadata["inputs"]["fail-on"]["default"] == "high"
    assert metadata["inputs"]["report-format"]["default"] == "markdown"
    assert metadata["inputs"]["report-path"]["default"] == ""
    assert "report-path" in metadata["outputs"]


@pytest.mark.parametrize("value", sorted(entrypoint.VALID_FAIL_ON))
def test_valid_fail_on_values_are_accepted(value: str, tmp_path: Path) -> None:
    config = entrypoint.load_config(
        action_environment(tmp_path, ACTIONDOC_FAIL_ON=value)
    )

    assert config.fail_on == value


@pytest.mark.parametrize("value", ["", "info", "HIGHER"])
def test_invalid_fail_on_values_are_rejected(value: str, tmp_path: Path) -> None:
    with pytest.raises(entrypoint.ActionInputError, match="fail-on"):
        entrypoint.load_config(action_environment(tmp_path, ACTIONDOC_FAIL_ON=value))


@pytest.mark.parametrize("value", sorted(entrypoint.VALID_REPORT_FORMATS))
def test_valid_report_formats_are_accepted(value: str, tmp_path: Path) -> None:
    config = entrypoint.load_config(
        action_environment(tmp_path, ACTIONDOC_REPORT_FORMAT=value)
    )

    assert config.report_format == value


@pytest.mark.parametrize("value", ["terminal", "sarif", "MARKDOWNX"])
def test_invalid_report_formats_are_rejected(value: str, tmp_path: Path) -> None:
    with pytest.raises(entrypoint.ActionInputError, match="report-format"):
        entrypoint.load_config(
            action_environment(tmp_path, ACTIONDOC_REPORT_FORMAT=value)
        )


@pytest.mark.parametrize(
    ("key", "value", "message"),
    [
        ("ACTIONDOC_PATH", "", "path must not be empty"),
        (
            "ACTIONDOC_REPORT_PATH",
            "report\nname.md",
            "report-path must be a single valid path",
        ),
    ],
)
def test_invalid_path_inputs_are_rejected(
    key: str,
    value: str,
    message: str,
    tmp_path: Path,
) -> None:
    with pytest.raises(entrypoint.ActionInputError, match=message):
        entrypoint.load_config(action_environment(tmp_path, **{key: value}))


def test_none_mode_rejects_report_path(tmp_path: Path) -> None:
    with pytest.raises(entrypoint.ActionInputError, match="report-path"):
        entrypoint.load_config(
            action_environment(
                tmp_path,
                ACTIONDOC_REPORT_FORMAT="none",
                ACTIONDOC_REPORT_PATH="report.md",
            )
        )


def test_default_report_path_uses_runner_temp(tmp_path: Path) -> None:
    config = entrypoint.load_config(action_environment(tmp_path))

    assert config.report_path == tmp_path / "runner temp" / "actiondoc-report.md"


def test_custom_report_path_with_spaces_is_preserved(tmp_path: Path) -> None:
    report_path = tmp_path / "reports with spaces" / "audit.json"
    config = entrypoint.load_config(
        action_environment(
            tmp_path,
            ACTIONDOC_REPORT_FORMAT="json",
            ACTIONDOC_REPORT_PATH=str(report_path),
        )
    )

    assert config.report_path == report_path


def test_markdown_execution_writes_output_and_step_summary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    environment = action_environment(tmp_path)
    runner = FakeCommandRunner()
    monkeypatch.setattr(entrypoint, "run_command", runner)
    config = entrypoint.load_config(environment)

    exit_code = entrypoint.execute(config, environment, ROOT)

    assert exit_code == 0
    assert config.report_path is not None and config.report_path.is_file()
    assert f"report-path={config.report_path}" in Path(
        environment["GITHUB_OUTPUT"]
    ).read_text(encoding="utf-8")
    assert "# ActionDoc Report" in Path(environment["GITHUB_STEP_SUMMARY"]).read_text(
        encoding="utf-8"
    )
    scan_call = runner.calls[1]
    assert scan_call[scan_call.index("--format") + 1] == "markdown"
    assert scan_call[scan_call.index("--output") + 1] == str(config.report_path)


def test_json_execution_writes_report_without_step_summary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    environment = action_environment(tmp_path, ACTIONDOC_REPORT_FORMAT="json")
    runner = FakeCommandRunner()
    monkeypatch.setattr(entrypoint, "run_command", runner)
    config = entrypoint.load_config(environment)

    assert entrypoint.execute(config, environment, ROOT) == 0
    assert config.report_path is not None and config.report_path.suffix == ".json"
    assert Path(environment["GITHUB_STEP_SUMMARY"]).read_text(encoding="utf-8") == ""


def test_none_mode_uses_terminal_scan_and_returns_empty_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    environment = action_environment(tmp_path, ACTIONDOC_REPORT_FORMAT="none")
    runner = FakeCommandRunner()
    monkeypatch.setattr(entrypoint, "run_command", runner)
    config = entrypoint.load_config(environment)

    assert entrypoint.execute(config, environment, ROOT) == 0
    scan_call = runner.calls[1]
    assert "--output" not in scan_call
    assert scan_call[scan_call.index("--format") + 1] == "terminal"
    assert Path(environment["GITHUB_OUTPUT"]).read_text(encoding="utf-8") == (
        "report-path=\n"
    )


def test_scan_exit_code_one_is_preserved_after_report_generation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    environment = action_environment(tmp_path, ACTIONDOC_REPORT_FORMAT="json")
    runner = FakeCommandRunner(scan_returncode=1)
    monkeypatch.setattr(entrypoint, "run_command", runner)
    config = entrypoint.load_config(environment)

    assert entrypoint.execute(config, environment, ROOT) == 1
    assert config.report_path is not None and config.report_path.is_file()
    assert f"report-path={config.report_path}" in Path(
        environment["GITHUB_OUTPUT"]
    ).read_text(encoding="utf-8")


def test_invalid_repository_exit_code_is_preserved_without_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    environment = action_environment(tmp_path)
    runner = FakeCommandRunner(scan_returncode=2)
    monkeypatch.setattr(entrypoint, "run_command", runner)
    config = entrypoint.load_config(environment)

    assert entrypoint.execute(config, environment, ROOT) == 2
    assert config.report_path is not None
    assert not config.report_path.exists()
    assert Path(environment["GITHUB_OUTPUT"]).read_text(encoding="utf-8") == (
        "report-path=\n"
    )


def test_no_shell_injection_is_possible_through_path_input(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    injected_path = "fixture; touch should-not-run"
    environment = action_environment(tmp_path, ACTIONDOC_PATH=injected_path)
    runner = FakeCommandRunner()
    monkeypatch.setattr(entrypoint, "run_command", runner)
    config = entrypoint.load_config(environment)

    assert entrypoint.execute(config, environment, ROOT) == 0
    scan_call = runner.calls[1]
    assert injected_path in scan_call
    assert all(argument != "touch should-not-run" for argument in scan_call)


def test_entrypoint_works_without_github_output_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    environment = action_environment(tmp_path, ACTIONDOC_REPORT_FORMAT="none")
    environment.pop("GITHUB_OUTPUT")
    environment.pop("GITHUB_STEP_SUMMARY")
    runner = FakeCommandRunner()
    monkeypatch.setattr(entrypoint, "run_command", runner)

    assert (
        entrypoint.execute(entrypoint.load_config(environment), environment, ROOT) == 0
    )


def test_main_rejects_invalid_input_without_running_commands(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(entrypoint.os, "environ", {"ACTIONDOC_FAIL_ON": "invalid"})

    assert entrypoint.main() == 2


def test_ci_uses_pinned_actions_and_exercises_the_local_action() -> None:
    """The repository CI validates the composite action without publication."""
    yaml = YAML(typ="safe")
    workflow = yaml.load((ROOT / ".github" / "workflows" / "ci.yml").read_text())
    rendered = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert workflow["jobs"]["action-integration"]["permissions"] == {"contents": "read"}
    assert "uses: ./" in rendered
    assert "actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683" in rendered
    assert "actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065" in rendered
