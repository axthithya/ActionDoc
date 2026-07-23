"""Focused positive, negative, and helper tests for cost-efficiency rules."""

from pathlib import Path

import pytest

from actiondoctor.engine import RuleEngine
from actiondoctor.models import Severity, WorkflowFile, WorkflowParseError
from actiondoctor.parser import WorkflowParser
from actiondoctor.registry import DEFAULT_REGISTRY
from actiondoctor.rules.cost import (
    LargeMatrixRule,
    MissingConcurrencyCancellationRule,
    MissingNodeCacheRule,
    MissingPythonCacheRule,
    UnrestrictedPushRule,
)
from actiondoctor.rules.cost.helpers import (
    NODE_INSTALL,
    PYTHON_INSTALL,
    static_matrix_size,
)


def workflow(yaml_text: str) -> WorkflowFile:
    """Parse inline YAML through the production parser."""
    path = Path("repository/.github/workflows/cost.yml")
    result = WorkflowParser().parse(
        path=path,
        relative_path=".github/workflows/cost.yml",
        raw_text=yaml_text,
    )
    assert not isinstance(result, WorkflowParseError)
    return result


def job_workflow(steps: str) -> WorkflowFile:
    """Build a minimal workflow with caller-provided step YAML."""
    return workflow(
        f"""name: Cost test
on: workflow_dispatch
permissions:
  contents: read
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
{steps}
"""
    )


def test_default_registry_contains_cost_rules_in_deterministic_order() -> None:
    assert [rule.rule_id for rule in DEFAULT_REGISTRY.rules] == [
        "COST001",
        "COST002",
        "COST003",
        "COST004",
        "COST005",
        "MAINT001",
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


@pytest.mark.parametrize(
    "trigger", ["pull_request", "[push, pull_request]", "pull_request_target"]
)
def test_cost001_reports_pull_request_triggers_without_cancellation(
    trigger: str,
) -> None:
    findings = MissingConcurrencyCancellationRule().evaluate(
        workflow(f"name: PR\non: {trigger}\njobs: {{}}\n")
    )
    assert len(findings) == 1
    assert findings[0].severity is Severity.MEDIUM
    assert findings[0].yaml_path == "concurrency"


def test_cost001_accepts_literal_cancellation_and_group_expression() -> None:
    parsed = workflow(
        """name: PR
on:
  pull_request:
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
jobs: {}
"""
    )
    assert MissingConcurrencyCancellationRule().evaluate(parsed) == []


@pytest.mark.parametrize("trigger", ["push", "schedule", "workflow_dispatch"])
def test_cost001_ignores_non_pull_request_workflows(trigger: str) -> None:
    assert (
        MissingConcurrencyCancellationRule().evaluate(
            workflow(f"name: Other\non: {trigger}\njobs: {{}}\n")
        )
        == []
    )


def test_cost001_reports_expression_cancellation_as_uncertain() -> None:
    findings = MissingConcurrencyCancellationRule().evaluate(
        workflow(
            """name: PR
on: pull_request
concurrency:
  group: pr
  cancel-in-progress: ${{ github.event_name == 'pull_request' }}
jobs: {}
"""
        )
    )
    assert len(findings) == 1
    assert "cannot be confirmed statically" in findings[0].description
    assert findings[0].yaml_path == "concurrency.cancel-in-progress"


def test_cost001_ignores_explicitly_disabled_pull_request_trigger() -> None:
    parsed = workflow("name: Disabled\non:\n  pull_request: false\njobs: {}\n")
    assert MissingConcurrencyCancellationRule().evaluate(parsed) == []


@pytest.mark.parametrize(
    "command",
    [
        "pip install -r requirements.txt",
        "python -m pip install .",
        "poetry install",
        "pipenv install --dev",
    ],
)
def test_cost002_reports_supported_python_installs(command: str) -> None:
    findings = MissingPythonCacheRule().evaluate(
        job_workflow(
            f"""      - uses: actions/setup-python@v5
      - run: {command}
"""
        )
    )
    assert len(findings) == 1
    assert findings[0].job_id == "test"
    assert findings[0].yaml_path == "jobs.test.steps[1].run"
    assert findings[0].line is not None


@pytest.mark.parametrize(
    "steps",
    [
        """      - uses: actions/setup-python@v5
        with:
          cache: pip
      - run: pip install -r requirements.txt
""",
        """      - uses: actions/setup-python@v5
      - uses: actions/cache@v4
        with:
          path: ~/.cache/pip
          key: pip
      - run: pip install -r requirements.txt
""",
        """      - uses: actions/setup-python@v5
      - run: python --version
""",
    ],
)
def test_cost002_ignores_cached_or_non_installing_jobs(steps: str) -> None:
    assert MissingPythonCacheRule().evaluate(job_workflow(steps)) == []


def test_cost002_cache_after_install_does_not_protect_installation() -> None:
    findings = MissingPythonCacheRule().evaluate(
        job_workflow(
            """      - uses: actions/setup-python@v5
      - run: pip install -r requirements.txt
      - uses: actions/cache@v4
"""
        )
    )
    assert len(findings) == 1


@pytest.mark.parametrize(
    "command", ["npm install", "npm ci", "yarn install --immutable", "pnpm install"]
)
def test_cost003_reports_supported_node_installs(command: str) -> None:
    findings = MissingNodeCacheRule().evaluate(
        job_workflow(
            f"""      - uses: actions/setup-node@v4
      - run: {command}
"""
        )
    )
    assert len(findings) == 1
    assert findings[0].severity is Severity.LOW


@pytest.mark.parametrize(
    "steps",
    [
        """      - uses: actions/setup-node@v4
        with:
          cache: npm
      - run: npm ci
""",
        """      - uses: actions/setup-node@v4
      - uses: actions/cache@v4
      - run: yarn install
""",
        """      - uses: actions/setup-node@v4
      - run: npm test
""",
    ],
)
def test_cost003_ignores_cached_or_non_installing_jobs(steps: str) -> None:
    assert MissingNodeCacheRule().evaluate(job_workflow(steps)) == []


@pytest.mark.parametrize("trigger", ["push", "[push, workflow_dispatch]"])
def test_cost004_reports_unrestricted_scalar_or_list_push(trigger: str) -> None:
    findings = UnrestrictedPushRule().evaluate(
        workflow(f"name: Push\non: {trigger}\njobs: {{}}\n")
    )
    assert len(findings) == 1
    assert findings[0].yaml_path == "on.push"


def test_cost004_reports_empty_mapping_push() -> None:
    findings = UnrestrictedPushRule().evaluate(
        workflow("name: Push\non:\n  push: {}\njobs: {}\n")
    )
    assert len(findings) == 1
    assert findings[0].line == 3


@pytest.mark.parametrize(
    "filter_name", ["branches", "branches-ignore", "paths", "paths-ignore", "tags"]
)
def test_cost004_ignores_filtered_push(filter_name: str) -> None:
    parsed = workflow(
        f"name: Push\non:\n  push:\n    {filter_name}: [main]\njobs: {{}}\n"
    )
    assert UnrestrictedPushRule().evaluate(parsed) == []


@pytest.mark.parametrize(
    "trigger_yaml",
    ["on: pull_request", "on:\n  push: false", "on:\n  push: ${{ inputs.event }}"],
)
def test_cost004_ignores_absent_disabled_or_ambiguous_push(
    trigger_yaml: str,
) -> None:
    parsed = workflow(f"name: Other\n{trigger_yaml}\njobs: {{}}\n")
    assert UnrestrictedPushRule().evaluate(parsed) == []


@pytest.mark.parametrize(("size", "expected"), [(12, 0), (13, 1), (6, 0)])
def test_cost005_threshold_boundary(size: int, expected: int) -> None:
    values = ", ".join(str(value) for value in range(size))
    parsed = workflow(
        f"""name: Matrix
on: workflow_dispatch
jobs:
  test:
    strategy:
      matrix:
        item: [{values}]
"""
    )
    findings = LargeMatrixRule().evaluate(parsed)
    assert len(findings) == expected


def test_cost005_reports_product_and_static_include_count() -> None:
    parsed = workflow(
        """name: Matrix
on: workflow_dispatch
jobs:
  test:
    strategy:
      matrix:
        os: [ubuntu, windows, macos]
        python: ["3.10", "3.11", "3.12", "3.13", "3.14"]
        include:
          - os: ubuntu
            python: pypy
        exclude:
          - os: windows
            python: "3.10"
"""
    )
    findings = LargeMatrixRule().evaluate(parsed)
    assert len(findings) == 1
    assert "15 combinations" in findings[0].description
    assert "1 static `include`" in findings[0].description
    assert findings[0].job_id == "test"
    assert findings[0].yaml_path == "jobs.test.strategy.matrix"


@pytest.mark.parametrize(
    "matrix",
    [
        "${{ fromJSON(inputs.matrix) }}",
        "invalid",
        '{os: "${{ inputs.os }}"}',
    ],
)
def test_cost005_ignores_dynamic_or_invalid_matrix_shapes(matrix: str) -> None:
    parsed = workflow(
        f"name: Matrix\non: workflow_dispatch\njobs:\n  test:\n"
        f"    strategy:\n      matrix: {matrix}\n"
    )
    assert LargeMatrixRule().evaluate(parsed) == []


def test_cost005_ignores_list_dimension_containing_expression() -> None:
    values = ", ".join(str(value) for value in range(12))
    parsed = workflow(
        "name: Dynamic\non: workflow_dispatch\njobs:\n  test:\n"
        "    strategy:\n      matrix:\n"
        f'        item: [{values}, "${{{{ inputs.extra }}}}"]\n'
    )
    assert LargeMatrixRule().evaluate(parsed) == []


def test_helpers_match_only_command_boundaries_and_count_static_matrices() -> None:
    assert PYTHON_INSTALL.search("echo pip install package") is None
    assert NODE_INSTALL.search("echo npm ci") is None
    assert NODE_INSTALL.search("npm test && npm ci") is not None
    size = static_matrix_size(
        {"os": ["linux", "windows"], "python": ["3.11", "3.12"], "include": [{}]}
    )
    assert size is not None
    assert size.base_combinations == 4
    assert size.include_additions == 1


def test_multiple_jobs_produce_distinct_findings_without_duplicates() -> None:
    parsed = workflow(
        """name: Multiple
on: pull_request
jobs:
  python:
    steps:
      - uses: actions/setup-python@v5
      - run: pip install .
      - run: pip install -r requirements.txt
  node:
    steps:
      - uses: actions/setup-node@v4
      - run: npm ci
"""
    )
    findings = (
        MissingConcurrencyCancellationRule().evaluate(parsed)
        + MissingPythonCacheRule().evaluate(parsed)
        + MissingNodeCacheRule().evaluate(parsed)
    )
    assert [finding.rule_id for finding in findings] == [
        "COST001",
        "COST002",
        "COST003",
    ]
    assert len({(finding.rule_id, finding.job_id) for finding in findings}) == 3


def test_cost_finding_engine_order_is_deterministic() -> None:
    parsed = workflow(
        """name: Ordered
on: [push, pull_request]
jobs:
  python:
    steps:
      - uses: actions/setup-python@v5
      - run: pip install .
"""
    )
    result = RuleEngine().run(
        [parsed],
        [
            UnrestrictedPushRule(),
            MissingPythonCacheRule(),
            MissingConcurrencyCancellationRule(),
        ],
    )
    assert [finding.rule_id for finding in result.findings] == [
        "COST002",
        "COST001",
        "COST004",
    ]
