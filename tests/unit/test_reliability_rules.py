"""Focused tests for the production reliability rule pack."""

from pathlib import Path

import pytest

from actiondoctor.engine import RuleEngine
from actiondoctor.models import Severity, WorkflowFile, WorkflowParseError
from actiondoctor.parser import WorkflowParser
from actiondoctor.registry import DEFAULT_REGISTRY
from actiondoctor.rules.reliability import (
    ContinueOnErrorRule,
    MissingJobTimeoutRule,
    MovingRunnerLabelRule,
    MutableContainerImageRule,
    ServiceWithoutHealthCheckRule,
)
from actiondoctor.rules.reliability.helpers import (
    has_health_check,
    is_mutable_image_reference,
    moving_runner_labels,
)


def workflow(yaml_text: str) -> WorkflowFile:
    """Parse inline YAML through the production parser."""
    path = Path("repository/.github/workflows/reliability.yml")
    result = WorkflowParser().parse(
        path=path,
        relative_path=".github/workflows/reliability.yml",
        raw_text=yaml_text,
    )
    assert not isinstance(result, WorkflowParseError)
    return result


def jobs_workflow(jobs: str) -> WorkflowFile:
    """Create a workflow with caller-provided job definitions."""
    return workflow(
        f"""name: Reliability test
on: workflow_dispatch
permissions:
  contents: read
jobs:
{jobs}
"""
    )


def test_default_registry_contains_complete_reliability_pack() -> None:
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


def test_rel002_reports_job_without_timeout_with_job_location() -> None:
    findings = MissingJobTimeoutRule().evaluate(
        jobs_workflow("  test:\n    runs-on: ubuntu-24.04\n")
    )

    assert len(findings) == 1
    assert findings[0].severity is Severity.MEDIUM
    assert findings[0].job_id == "test"
    assert findings[0].yaml_path == "jobs.test.timeout-minutes"
    assert findings[0].line == 6


@pytest.mark.parametrize("timeout", ["1", "30", "0.5"])
def test_rel002_accepts_positive_static_timeout(timeout: str) -> None:
    parsed = jobs_workflow(
        f"  test:\n    runs-on: ubuntu-24.04\n    timeout-minutes: {timeout}\n"
    )
    assert MissingJobTimeoutRule().evaluate(parsed) == []


@pytest.mark.parametrize(
    "job_yaml",
    [
        "  reusable:\n    uses: owner/repository/.github/workflows/ci.yml@main\n",
        "  malformed\n",
    ],
)
def test_rel002_ignores_reusable_or_malformed_jobs(job_yaml: str) -> None:
    assert MissingJobTimeoutRule().evaluate(jobs_workflow(job_yaml)) == []


def test_rel002_ignores_dynamic_timeout_and_reports_nonpositive_values() -> None:
    dynamic = jobs_workflow("  test:\n    timeout-minutes: ${{ inputs.timeout }}\n")
    assert MissingJobTimeoutRule().evaluate(dynamic) == []

    invalid = jobs_workflow(
        "  zero:\n    timeout-minutes: 0\n  negative:\n    timeout-minutes: -1\n"
    )
    findings = MissingJobTimeoutRule().evaluate(invalid)
    assert [finding.job_id for finding in findings] == ["zero", "negative"]


def test_rel002_reports_each_affected_job_once() -> None:
    parsed = jobs_workflow("  first: {}\n  second: {}\n")
    findings = MissingJobTimeoutRule().evaluate(parsed)
    assert [finding.job_id for finding in findings] == ["first", "second"]


@pytest.mark.parametrize("image", ["postgres", "postgres:latest", "redis:nightly"])
def test_rel003_reports_mutable_job_container_images(image: str) -> None:
    parsed = jobs_workflow(
        f"  test:\n    timeout-minutes: 10\n    container:\n      image: {image}\n"
    )
    findings = MutableContainerImageRule().evaluate(parsed)

    assert len(findings) == 1
    assert findings[0].severity is Severity.MEDIUM
    assert findings[0].yaml_path == "jobs.test.container.image"
    assert findings[0].line is not None


@pytest.mark.parametrize(
    "image",
    [
        "postgres:16.3",
        "redis:7.2.5",
        "localhost:5000/image:1.2",
        "ghcr.io/example/app@sha256:"
        "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
        "${{ inputs.image }}",
    ],
)
def test_rel003_ignores_fixed_digest_or_dynamic_images(image: str) -> None:
    parsed = jobs_workflow(
        f"  test:\n    timeout-minutes: 10\n    container:\n      image: {image}\n"
    )
    assert MutableContainerImageRule().evaluate(parsed) == []


def test_rel003_handles_registry_port_without_confusing_it_for_tag() -> None:
    assert is_mutable_image_reference("localhost:5000/image") is True
    assert is_mutable_image_reference("localhost:5000/image:1.2") is False


def test_rel003_reports_job_and_multiple_service_image_locations() -> None:
    parsed = jobs_workflow(
        """  test:
    timeout-minutes: 10
    container:
      image: python
    services:
      database:
        image: postgres:latest
      cache:
        image: redis
"""
    )
    findings = MutableContainerImageRule().evaluate(parsed)
    assert [finding.yaml_path for finding in findings] == [
        "jobs.test.container.image",
        "jobs.test.services.database.image",
        "jobs.test.services.cache.image",
    ]


@pytest.mark.parametrize("label", ["ubuntu-latest", "windows-latest", "macos-latest"])
def test_rel004_reports_moving_scalar_runner_labels(label: str) -> None:
    findings = MovingRunnerLabelRule().evaluate(
        jobs_workflow(f"  test:\n    runs-on: {label}\n    timeout-minutes: 10\n")
    )
    assert len(findings) == 1
    assert findings[0].severity is Severity.LOW
    assert findings[0].yaml_path == "jobs.test.runs-on"


@pytest.mark.parametrize(
    "label", ["ubuntu-24.04", "windows-2025", "macos-15", "self-hosted"]
)
def test_rel004_ignores_versioned_and_self_hosted_labels(label: str) -> None:
    parsed = jobs_workflow(f"  test:\n    runs-on: {label}\n    timeout-minutes: 10\n")
    assert MovingRunnerLabelRule().evaluate(parsed) == []


def test_rel004_detects_static_list_but_ignores_dynamic_lists() -> None:
    static = jobs_workflow(
        "  test:\n    runs-on: [self-hosted, ubuntu-latest]\n    timeout-minutes: 10\n"
    )
    assert len(MovingRunnerLabelRule().evaluate(static)) == 1

    dynamic = jobs_workflow(
        '  test:\n    runs-on: ["${{ matrix.os }}", ubuntu-latest]\n'
        "    timeout-minutes: 10\n"
    )
    assert MovingRunnerLabelRule().evaluate(dynamic) == []
    assert moving_runner_labels("${{ matrix.os }}") == ()


def test_rel005_reports_job_level_true_as_high() -> None:
    findings = ContinueOnErrorRule().evaluate(
        jobs_workflow(
            "  test:\n    runs-on: ubuntu-24.04\n"
            "    timeout-minutes: 10\n    continue-on-error: true\n"
        )
    )
    assert len(findings) == 1
    assert findings[0].severity is Severity.HIGH
    assert findings[0].yaml_path == "jobs.test.continue-on-error"
    assert findings[0].line is not None


def test_rel005_reports_named_step_true_as_medium_with_index() -> None:
    findings = ContinueOnErrorRule().evaluate(
        jobs_workflow(
            """  test:
    runs-on: ubuntu-24.04
    timeout-minutes: 10
    steps:
      - name: Optional lint
        run: lint
        continue-on-error: true
"""
        )
    )
    assert len(findings) == 1
    assert findings[0].severity is Severity.MEDIUM
    assert findings[0].yaml_path == "jobs.test.steps[0].continue-on-error"
    assert "Optional lint" in findings[0].description
    assert "index 0" in findings[0].description


@pytest.mark.parametrize("value", ["false", "${{ matrix.experimental }}"])
def test_rel005_ignores_false_and_dynamic_values(value: str) -> None:
    parsed = jobs_workflow(
        f"  test:\n    continue-on-error: {value}\n"
        "    steps:\n"
        f"      - run: test\n        continue-on-error: {value}\n"
    )
    assert ContinueOnErrorRule().evaluate(parsed) == []


def test_rel005_reports_multiple_affected_steps_without_duplicates() -> None:
    parsed = jobs_workflow(
        """  test:
    steps:
      - run: first
        continue-on-error: true
      - run: second
        continue-on-error: true
"""
    )
    findings = ContinueOnErrorRule().evaluate(parsed)
    assert [finding.yaml_path for finding in findings] == [
        "jobs.test.steps[0].continue-on-error",
        "jobs.test.steps[1].continue-on-error",
    ]


@pytest.mark.parametrize(
    "service_body",
    [
        "        image: postgres:16\n",
        "        image: postgres:16\n        options: --name database\n",
    ],
)
def test_rel006_reports_service_without_health_command(service_body: str) -> None:
    parsed = jobs_workflow(
        "  test:\n    timeout-minutes: 10\n    services:\n"
        "      database:\n"
        f"{service_body}"
    )
    findings = ServiceWithoutHealthCheckRule().evaluate(parsed)
    assert len(findings) == 1
    assert findings[0].severity is Severity.LOW
    assert findings[0].yaml_path == "jobs.test.services.database.options"
    assert findings[0].line is not None


def test_rel006_accepts_recognizable_health_command() -> None:
    parsed = jobs_workflow(
        """  test:
    services:
      database:
        image: postgres:16
        options: >-
          --health-cmd "pg_isready"
          --health-interval 10s
"""
    )
    assert ServiceWithoutHealthCheckRule().evaluate(parsed) == []
    assert has_health_check("--health-cmd=ready") is True


def test_rel006_reports_multiple_services_and_ignores_invalid_shapes() -> None:
    parsed = jobs_workflow(
        """  test:
    services:
      database:
        image: postgres:16
      cache:
        image: redis:7
      malformed: redis
      missing-image:
        options: --name absent
      dynamic:
        image: ${{ inputs.image }}
      dynamic-options:
        image: search:1
        options: ${{ inputs.options }}
"""
    )
    findings = ServiceWithoutHealthCheckRule().evaluate(parsed)
    assert [finding.yaml_path for finding in findings] == [
        "jobs.test.services.database.options",
        "jobs.test.services.cache.options",
    ]


def test_multiple_reliability_findings_are_deterministic_and_unique() -> None:
    parsed = jobs_workflow(
        """  test:
    runs-on: ubuntu-latest
    container:
      image: python:latest
    continue-on-error: true
    services:
      database:
        image: postgres
    steps:
      - run: optional
        continue-on-error: true
"""
    )
    rules = [
        ServiceWithoutHealthCheckRule(),
        ContinueOnErrorRule(),
        MovingRunnerLabelRule(),
        MutableContainerImageRule(),
        MissingJobTimeoutRule(),
    ]
    first = RuleEngine().run([parsed], rules)
    second = RuleEngine().run([parsed], reversed(rules))

    assert first.findings == second.findings
    identities = [(finding.rule_id, finding.yaml_path) for finding in first.findings]
    assert len(identities) == len(set(identities)) == 7
