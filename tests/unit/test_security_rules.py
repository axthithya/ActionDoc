"""Focused positive and negative tests for the initial security rule pack."""

from pathlib import Path

import pytest

from actiondoctor.models import Severity, WorkflowFile, WorkflowParseError
from actiondoctor.parser import WorkflowParser
from actiondoctor.registry import DEFAULT_REGISTRY
from actiondoctor.rules.security import (
    BroadPermissionsRule,
    MissingExplicitPermissionsRule,
    PullRequestTargetCheckoutRule,
    UnpinnedActionRule,
    WorkflowSecretEnvironmentRule,
)

FIXTURES = Path(__file__).parents[1] / "fixtures" / "security"


def workflow_fixture(name: str) -> WorkflowFile:
    """Parse one security fixture through the production parser."""
    path = FIXTURES / name
    result = WorkflowParser().parse(
        path=path,
        relative_path=f".github/workflows/{name}",
        raw_text=path.read_text(encoding="utf-8"),
    )
    assert not isinstance(result, WorkflowParseError)
    return result


def test_default_registry_contains_all_active_rules_in_order() -> None:
    """Cost, security, and the two earlier rules are explicitly active."""
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


def test_sec001_reports_write_all_as_critical() -> None:
    """The write-all shorthand is the broadest permission grant."""
    findings = BroadPermissionsRule().evaluate(
        workflow_fixture("permissions_write_all.yml")
    )

    assert len(findings) == 1
    assert findings[0].severity is Severity.CRITICAL
    assert findings[0].yaml_path == "permissions"
    assert findings[0].line == 3


def test_sec001_reports_all_write_mapping_as_high() -> None:
    """Multiple declared scopes all set to write are broadly writable."""
    findings = BroadPermissionsRule().evaluate(
        workflow_fixture("permissions_all_write.yml")
    )

    assert len(findings) == 1
    assert findings[0].severity is Severity.HIGH


@pytest.mark.parametrize(
    "fixture", ["permissions_read_all.yml", "permissions_narrow.yml"]
)
def test_sec001_ignores_read_all_and_narrow_permissions(fixture: str) -> None:
    """Read-only and mixed least-privilege mappings are not broad-write findings."""
    assert BroadPermissionsRule().evaluate(workflow_fixture(fixture)) == []


def test_sec002_reports_missing_permissions_once() -> None:
    """Undeclared workflow/job defaults produce one workflow-level finding."""
    findings = MissingExplicitPermissionsRule().evaluate(
        workflow_fixture("missing_permissions.yml")
    )

    assert len(findings) == 1
    assert findings[0].severity is Severity.MEDIUM
    assert findings[0].yaml_path == "permissions"


@pytest.mark.parametrize(
    "fixture", ["permissions_narrow.yml", "every_job_permissions.yml"]
)
def test_sec002_accepts_top_level_or_complete_per_job_permissions(
    fixture: str,
) -> None:
    """Explicit top-level or every-job declarations avoid inherited defaults."""
    assert MissingExplicitPermissionsRule().evaluate(workflow_fixture(fixture)) == []


@pytest.mark.parametrize("fixture", ["action_version.yml", "action_branch.yml"])
def test_sec003_reports_mutable_action_references(fixture: str) -> None:
    """Version tags and branches are mutable third-party references."""
    findings = UnpinnedActionRule().evaluate(workflow_fixture(fixture))

    assert len(findings) == 1
    assert findings[0].severity is Severity.HIGH
    assert findings[0].job_id == "build"
    assert findings[0].yaml_path == "jobs.build.steps[0].uses"
    assert findings[0].line is not None
    assert "@" in findings[0].description


@pytest.mark.parametrize(
    "fixture",
    ["action_sha.yml", "action_local.yml", "action_docker.yml", "reusable_job.yml"],
)
def test_sec003_ignores_immutable_or_non_third_party_references(
    fixture: str,
) -> None:
    """Full SHAs, local/docker steps, and job reusable workflows are exempt."""
    assert UnpinnedActionRule().evaluate(workflow_fixture(fixture)) == []


def test_sec003_reports_each_distinct_insecure_step() -> None:
    """Multiple mutable actions produce distinct YAML-located findings."""
    findings = UnpinnedActionRule().evaluate(workflow_fixture("multiple_unpinned.yml"))

    assert len(findings) == 2
    assert [finding.yaml_path for finding in findings] == [
        "jobs.build.steps[0].uses",
        "jobs.build.steps[1].uses",
    ]
    assert len({finding.line for finding in findings}) == 2


def test_sec004_reports_risky_pull_request_target_checkout() -> None:
    """An explicit PR-head ref under pull_request_target is conservatively risky."""
    findings = PullRequestTargetCheckoutRule().evaluate(
        workflow_fixture("risky_pull_request_target.yml")
    )

    assert len(findings) == 1
    assert findings[0].severity is Severity.CRITICAL
    assert findings[0].job_id == "inspect"
    assert findings[0].yaml_path == "jobs.inspect.steps[0].with.ref"
    assert findings[0].line is not None
    assert "appears" in findings[0].description


@pytest.mark.parametrize(
    "fixture", ["safe_pull_request.yml", "pull_request_target_no_checkout.yml"]
)
def test_sec004_avoids_safe_or_unrelated_workflows(fixture: str) -> None:
    """Normal pull_request and target workflows without checkout are not flagged."""
    assert PullRequestTargetCheckoutRule().evaluate(workflow_fixture(fixture)) == []


def test_sec005_reports_workflow_level_secret_reference() -> None:
    """Broad workflow env secret exposure is reported with the env YAML path."""
    findings = WorkflowSecretEnvironmentRule().evaluate(
        workflow_fixture("workflow_secret_env.yml")
    )

    assert len(findings) == 1
    assert findings[0].severity is Severity.MEDIUM
    assert findings[0].yaml_path == "env.TOKEN"
    assert findings[0].line is not None


@pytest.mark.parametrize("fixture", ["job_secret_env.yml", "step_secret_env.yml"])
def test_sec005_ignores_narrower_secret_scopes(fixture: str) -> None:
    """Job and step environment scopes are outside SEC005."""
    assert WorkflowSecretEnvironmentRule().evaluate(workflow_fixture(fixture)) == []


def test_security_rules_tolerate_malformed_job_and_step_shapes() -> None:
    """Malformed partial structures never crash individual security rules."""
    workflow = workflow_fixture("malformed_shapes.yml")
    rules = [
        BroadPermissionsRule(),
        MissingExplicitPermissionsRule(),
        UnpinnedActionRule(),
        PullRequestTargetCheckoutRule(),
        WorkflowSecretEnvironmentRule(),
    ]

    results = [rule.evaluate(workflow) for rule in rules]

    assert len(results) == 5
