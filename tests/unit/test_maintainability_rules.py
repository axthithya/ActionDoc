"""Focused tests for the production maintainability rule pack."""

from pathlib import Path

import pytest

from actiondoctor.engine import RuleEngine
from actiondoctor.models import Severity, WorkflowFile, WorkflowParseError
from actiondoctor.parser import WorkflowParser
from actiondoctor.registry import DEFAULT_REGISTRY
from actiondoctor.rules.maintainability import (
    DuplicateStepNameRule,
    LongInlineShellScriptRule,
    MissingJobNameRule,
    OversizedJobRule,
    UnnamedRunStepRule,
)
from actiondoctor.rules.maintainability.helpers import (
    non_empty_script_line_count,
    normalized_non_empty_string,
    normalized_step_name,
)
from actiondoctor.rules.maintainability.maint004_oversized_job import MAX_JOB_STEPS
from actiondoctor.rules.maintainability.maint006_long_inline_script import (
    MAX_INLINE_SCRIPT_LINES,
)


def workflow(yaml_text: str) -> WorkflowFile:
    """Parse inline YAML through the production parser."""
    path = Path("repository/.github/workflows/maintainability.yml")
    result = WorkflowParser().parse(
        path=path,
        relative_path=".github/workflows/maintainability.yml",
        raw_text=yaml_text,
    )
    assert not isinstance(result, WorkflowParseError)
    return result


def jobs_workflow(jobs: str) -> WorkflowFile:
    """Create a workflow with caller-provided jobs."""
    return workflow(
        f"""name: Maintainability test
on: workflow_dispatch
permissions:
  contents: read
jobs:
{jobs}
"""
    )


def steps_yaml(count: int, *, malformed: int = 0) -> str:
    """Render named run steps and optional invalid scalar entries."""
    steps = "".join(
        f"      - name: Step {index}\n        run: echo {index}\n"
        for index in range(count)
    )
    return steps + "      - invalid\n" * malformed


def script_step(line_count: int, *, blank_lines: bool = False) -> str:
    """Render one named block-scalar run step."""
    lines: list[str] = []
    for index in range(line_count):
        lines.append(f"          echo {index}\n")
        if blank_lines:
            lines.append("\n")
    return "      - name: Script\n        run: |\n" + "".join(lines)


def test_default_registry_contains_complete_maintainability_pack() -> None:
    assert [rule.rule_id for rule in DEFAULT_REGISTRY.rules] == [
        "COST001",
        "COST002",
        "COST003",
        "COST004",
        "COST005",
        "MAINT001",
        "MAINT002",
        "MAINT003",
        "MAINT004",
        "MAINT005",
        "MAINT006",
        "REL001",
        "REL002",
        "REL003",
        "REL004",
        "REL005",
        "REL006",
        "SEC001",
        "SEC002",
        "SEC003",
        "SEC004",
        "SEC005",
    ]


@pytest.mark.parametrize("name_yaml", ["", "    name: ''\n", "    name: '   '\n"])
def test_maint002_reports_missing_empty_or_blank_job_name(name_yaml: str) -> None:
    findings = MissingJobNameRule().evaluate(
        jobs_workflow(f"  test:\n{name_yaml}    timeout-minutes: 10\n")
    )
    assert len(findings) == 1
    assert findings[0].severity is Severity.LOW
    assert findings[0].job_id == "test"
    assert findings[0].yaml_path == "jobs.test.name"
    assert findings[0].line is not None


def test_maint002_accepts_named_job_and_ignores_reusable_or_malformed_jobs() -> None:
    parsed = jobs_workflow(
        """  named:
    name: Unit tests
  reusable:
    uses: owner/repo/.github/workflows/ci.yml@main
  malformed: invalid
"""
    )
    assert MissingJobNameRule().evaluate(parsed) == []


def test_maint002_reports_multiple_unnamed_jobs() -> None:
    findings = MissingJobNameRule().evaluate(
        jobs_workflow("  first: {}\n  second: {}\n")
    )
    assert [finding.job_id for finding in findings] == ["first", "second"]


@pytest.mark.parametrize(
    "step_yaml",
    [
        "      - run: echo test\n",
        "      - name: ''\n        run: echo test\n",
    ],
)
def test_maint003_reports_unnamed_or_empty_run_step(step_yaml: str) -> None:
    parsed = jobs_workflow(f"  test:\n    name: Test\n    steps:\n{step_yaml}")
    findings = UnnamedRunStepRule().evaluate(parsed)
    assert len(findings) == 1
    assert findings[0].yaml_path == "jobs.test.steps[0].name"
    assert "index 0" in findings[0].description
    assert findings[0].line is not None


def test_maint003_ignores_named_run_uses_and_invalid_steps() -> None:
    parsed = jobs_workflow(
        """  test:
    name: Test
    steps:
      - name: Run tests
        run: pytest
      - uses: actions/checkout@v4
      - invalid
      - run: [invalid]
"""
    )
    assert UnnamedRunStepRule().evaluate(parsed) == []


def test_maint003_reports_multiple_unnamed_run_steps() -> None:
    parsed = jobs_workflow(
        """  test:
    name: Test
    steps:
      - run: first
      - run: second
"""
    )
    findings = UnnamedRunStepRule().evaluate(parsed)
    assert [finding.yaml_path for finding in findings] == [
        "jobs.test.steps[0].name",
        "jobs.test.steps[1].name",
    ]


@pytest.mark.parametrize(("count", "expected"), [(14, 0), (15, 0), (16, 1)])
def test_maint004_step_threshold(count: int, expected: int) -> None:
    parsed = jobs_workflow(f"  test:\n    name: Test\n    steps:\n{steps_yaml(count)}")
    findings = OversizedJobRule().evaluate(parsed)
    assert len(findings) == expected
    if findings:
        assert "16 valid steps" in findings[0].description
        assert findings[0].severity is Severity.MEDIUM


def test_maint004_does_not_count_malformed_step_entries() -> None:
    parsed = jobs_workflow(
        f"  test:\n    name: Test\n    steps:\n{steps_yaml(15, malformed=3)}"
    )
    assert OversizedJobRule().evaluate(parsed) == []


def test_maint004_reports_multiple_oversized_jobs() -> None:
    parsed = jobs_workflow(
        f"  first:\n    name: First\n    steps:\n{steps_yaml(16)}"
        f"  second:\n    name: Second\n    steps:\n{steps_yaml(16)}"
    )
    findings = OversizedJobRule().evaluate(parsed)
    assert [finding.job_id for finding in findings] == ["first", "second"]
    assert MAX_JOB_STEPS == 15


@pytest.mark.parametrize("second_name", ["Run tests", "run TESTS", "  Run tests  "])
def test_maint005_reports_normalized_duplicate_after_first(
    second_name: str,
) -> None:
    parsed = jobs_workflow(
        f"""  test:
    name: Test
    steps:
      - name: Run tests
        run: pytest
      - name: {second_name}
        run: npm test
"""
    )
    findings = DuplicateStepNameRule().evaluate(parsed)
    assert len(findings) == 1
    assert findings[0].yaml_path == "jobs.test.steps[1].name"
    assert second_name.strip() in findings[0].description


def test_maint005_does_not_compare_across_jobs_or_report_empty_names() -> None:
    parsed = jobs_workflow(
        """  first:
    name: First
    steps:
      - name: Same
        run: first
      - name: ''
        run: empty
  second:
    name: Second
    steps:
      - name: Same
        run: second
      - name: '   '
        run: blank
"""
    )
    assert DuplicateStepNameRule().evaluate(parsed) == []


def test_maint005_reports_every_duplicate_after_first() -> None:
    parsed = jobs_workflow(
        """  test:
    name: Test
    steps:
      - name: Build
        run: first
      - name: BUILD
        run: second
      - name: build
        run: third
"""
    )
    findings = DuplicateStepNameRule().evaluate(parsed)
    assert [finding.yaml_path for finding in findings] == [
        "jobs.test.steps[1].name",
        "jobs.test.steps[2].name",
    ]


@pytest.mark.parametrize(("count", "expected"), [(19, 0), (20, 0), (21, 1)])
def test_maint006_non_empty_line_threshold(count: int, expected: int) -> None:
    parsed = jobs_workflow(f"  test:\n    name: Test\n    steps:\n{script_step(count)}")
    findings = LongInlineShellScriptRule().evaluate(parsed)
    assert len(findings) == expected
    if findings:
        assert "21 non-empty script lines" in findings[0].description
        assert findings[0].yaml_path == "jobs.test.steps[0].run"


def test_maint006_excludes_blank_lines() -> None:
    parsed = jobs_workflow(
        f"  test:\n    name: Test\n    steps:\n{script_step(20, blank_lines=True)}"
    )
    assert LongInlineShellScriptRule().evaluate(parsed) == []


def test_maint006_reports_multiple_long_scripts_and_ignores_non_string_run() -> None:
    long_step = script_step(21)
    parsed = jobs_workflow(
        f"  test:\n    name: Test\n    steps:\n{long_step}{long_step}"
        "      - name: Invalid\n        run: [not, scalar]\n"
    )
    findings = LongInlineShellScriptRule().evaluate(parsed)
    assert [finding.yaml_path for finding in findings] == [
        "jobs.test.steps[0].run",
        "jobs.test.steps[1].run",
    ]
    assert MAX_INLINE_SCRIPT_LINES == 20


def test_helpers_normalize_names_and_count_only_non_empty_lines() -> None:
    assert normalized_non_empty_string("  Name  ") == "Name"
    assert normalized_non_empty_string("  ") is None
    assert normalized_step_name("  RuN Tests ") == "run tests"
    assert non_empty_script_line_count("\n one \n\n two\n") == 2
    assert non_empty_script_line_count(["invalid"]) is None


def test_multiple_maintainability_findings_are_deterministic_and_unique() -> None:
    parsed = jobs_workflow(
        """  test:
    steps:
      - run: first
      - name: Duplicate
        run: second
      - name: duplicate
        run: third
"""
    )
    rules = [
        DuplicateStepNameRule(),
        UnnamedRunStepRule(),
        MissingJobNameRule(),
    ]
    first = RuleEngine().run([parsed], rules)
    second = RuleEngine().run([parsed], reversed(rules))

    assert first.findings == second.findings
    identities = [(finding.rule_id, finding.yaml_path) for finding in first.findings]
    assert len(identities) == len(set(identities)) == 3
