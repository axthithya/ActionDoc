"""Production security rules."""

from actiondoctor.rules.security.sec001_broad_permissions import BroadPermissionsRule
from actiondoctor.rules.security.sec002_missing_permissions import (
    MissingExplicitPermissionsRule,
)
from actiondoctor.rules.security.sec003_unpinned_action import UnpinnedActionRule
from actiondoctor.rules.security.sec004_pull_request_target_checkout import (
    PullRequestTargetCheckoutRule,
)
from actiondoctor.rules.security.sec005_workflow_secret_env import (
    WorkflowSecretEnvironmentRule,
)

__all__ = [
    "BroadPermissionsRule",
    "MissingExplicitPermissionsRule",
    "PullRequestTargetCheckoutRule",
    "UnpinnedActionRule",
    "WorkflowSecretEnvironmentRule",
]
